"""Guarded source-audit decision ingestion for the final CSV pass.

The Codex task supplies one JSON object per indexed source cell after inspecting
the 300-DPI evidence package.  This module deliberately keeps evidence
collection separate from CSV mutation: it validates complete immutable coverage,
then emits an atomic version-3 ledger consumed by :mod:`postprocessing`.
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from census_extractor.postprocessing import (
    CellReview,
    CorrectionLedger,
    TableReview,
    _expected_unique_cells,
    _sha256,
)
from census_extractor.schemas import SchemaRegistry


class SourceAuditError(ValueError):
    """Raised when source-audit evidence is incomplete or stale."""


class SourceAuditRunner:
    """Validate Codex decisions against an immutable verification package."""

    def __init__(self, provisional_root: Path, schemas_dir: Path):
        self.provisional_root = Path(provisional_root).resolve()
        self.schemas = SchemaRegistry(Path(schemas_dir))
        self.package_root = self.provisional_root / "codex_verification"
        self.manifest_path = self.package_root / "verification_manifest.json"
        self.index_path = self.package_root / "verification_index.jsonl"

    def write_queue(self, destination: Path) -> Path:
        """Write a deterministic, resumable audit queue from the index."""
        records = self._load_index(validate_evidence=False)
        destination = Path(destination).resolve()
        destination.parent.mkdir(parents=True, exist_ok=True)
        completed: dict[tuple[str, str, int, int | None, str], dict[str, Any]] = {}
        if destination.is_file():
            try:
                existing = [
                    json.loads(line)
                    for line in destination.read_text(encoding="utf-8").splitlines()
                    if line.strip()
                ]
            except (OSError, json.JSONDecodeError) as exc:
                raise SourceAuditError(f"cannot resume audit queue: {exc}") from exc
            indexed = {self._index_key(item): item for item in records}
            for number, payload in enumerate(existing, 1):
                if str(payload.get("status", "PENDING")) == "PENDING":
                    continue
                try:
                    pdf_id = str(payload["pdf_id"])
                    review = CellReview.model_validate(
                        {key: value for key, value in payload.items() if key != "pdf_id"}
                    )
                except (KeyError, TypeError, ValueError) as exc:
                    raise SourceAuditError(
                        f"invalid resumed decision at queue line {number}: {exc}"
                    ) from exc
                key = self._review_key(pdf_id, review)
                item = indexed.get(key)
                if item is None:
                    raise SourceAuditError(
                        f"resumed decision has no indexed source cell: {key}"
                    )
                self._validate_immutable(pdf_id, review, item)
                if key in completed:
                    raise SourceAuditError(f"duplicate resumed decision: {key}")
                completed[key] = payload
        temporary = destination.with_name(f".{destination.name}.{uuid.uuid4().hex}.tmp")
        with temporary.open("w", encoding="utf-8", newline="\n") as handle:
            for record in records:
                payload = {
                    "pdf_id": record["pdf_id"],
                    "selector": record["selector"],
                    "scope": record["scope"],
                    "variable": record["variable"],
                    "expected_original": record["provisional_value"],
                    "source_page": record["source_page"],
                    "panel_id": record["panel_id"],
                    "bbox": record["bbox"],
                    "crop_sha256": record["cell_crop_sha256"],
                    "evidence_sha256": record["cell_crop_sha256"],
                    "verification_method": "codex_source_audit",
                    "status": "PENDING",
                    "verified_value": record["provisional_value"],
                    "reason": "pending Codex source inspection",
                }
                prior = completed.get(self._index_key(record))
                if prior is not None:
                    payload.update(prior)
                handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")
        temporary.replace(destination)
        return destination

    def build_ledger(self, decisions_path: Path, destination: Path) -> CorrectionLedger:
        """Validate completed decisions and atomically write a version-3 ledger."""
        index_records = self._load_index(validate_evidence=True)
        indexed = {self._index_key(item): item for item in index_records}
        if len(indexed) != len(index_records):
            raise SourceAuditError("verification index contains duplicate selectors")
        decisions = self._load_decisions(decisions_path)
        by_key: dict[tuple[str, str, int, int | None, str], CellReview] = {}
        tables: dict[str, list[CellReview]] = {}
        for pdf_id, review in decisions:
            key = self._review_key(pdf_id, review)
            if key in by_key:
                raise SourceAuditError(f"duplicate source-audit decision: {key}")
            item = indexed.get(key)
            if item is None:
                raise SourceAuditError(f"decision has no indexed source cell: {key}")
            self._validate_immutable(pdf_id, review, item)
            by_key[key] = review
            tables.setdefault(pdf_id, []).append(review)

        missing = sorted(set(indexed).difference(by_key))
        if missing:
            raise SourceAuditError(
                f"source-audit coverage is incomplete: {len(missing)} cells missing"
            )
        manifest = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        source_manifest_sha = str(manifest["source_manifest_sha256"]).upper()
        if any(
            str(item.get("source_manifest_sha256", "")).upper() != source_manifest_sha
            for item in index_records
        ):
            raise SourceAuditError("verification index source-manifest lineage is inconsistent")
        table_reviews: dict[str, TableReview] = {}
        for pdf_id in sorted(tables):
            source_csv = self.provisional_root / "csv" / f"{pdf_id}.csv"
            if not source_csv.is_file():
                raise SourceAuditError(f"missing provisional CSV: {source_csv}")
            frame = pd.read_csv(source_csv, dtype=str, keep_default_na=False)
            index_item = next(item for item in index_records if item["pdf_id"] == pdf_id)
            format_id = str(index_item["format_id"])
            schema = self.schemas.require(format_id)
            expected = _expected_unique_cells(schema, frame)
            reviews = sorted(tables[pdf_id], key=self._sort_review)
            if len(reviews) != expected:
                raise SourceAuditError(
                    f"{pdf_id}: reviewed {len(reviews)} cells; expected {expected}"
                )
            parent_count = (
                len(set(str(value) for value in frame["parent_row_index"].tolist()))
                if schema.hierarchy is not None
                else len(frame)
            )
            pdf_sha = str(index_item["source_pdf_sha256"]).upper()
            table_reviews[pdf_id] = TableReview(
                format_id=format_id,
                expected_rows=len(frame),
                expected_parent_rows=parent_count,
                reviewed_unique_cells=expected,
                reviews=reviews,
                source_csv_sha256=_sha256(source_csv),
                source_pdf_sha256=pdf_sha,
            )
        ledger = CorrectionLedger(
            version=3,
            source_run_id=self.provisional_root.name,
            source_manifest_sha256=source_manifest_sha,
            expected_table_count=len(table_reviews),
            expected_output_rows=sum(table.expected_rows for table in table_reviews.values()),
            expected_unique_source_cells=len(index_records),
            tables=table_reviews,
            verification_method="codex_source_audit",
            verification_index_sha256=_sha256(self.index_path),
            allow_unresolved=any(
                review.status == "UNRESOLVED"
                for review in by_key.values()
            ),
        )
        destination = Path(destination).resolve()
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_name(f".{destination.name}.{uuid.uuid4().hex}.tmp")
        temporary.write_text(
            yaml.safe_dump(ledger.model_dump(mode="json"), sort_keys=False, allow_unicode=True),
            encoding="utf-8",
            newline="\n",
        )
        temporary.replace(destination)
        return ledger

    def _load_index(self, *, validate_evidence: bool = True) -> list[dict[str, Any]]:
        if not self.manifest_path.is_file() or not self.index_path.is_file():
            raise FileNotFoundError("Codex verification package is incomplete")
        manifest = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        actual_index_sha = _sha256(self.index_path)
        if manifest.get("verification_index_sha256") != actual_index_sha:
            raise SourceAuditError("verification index hash differs from package manifest")
        records = [
            json.loads(line)
            for line in self.index_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        if int(manifest.get("unique_source_cells", -1)) != len(records):
            raise SourceAuditError("verification index record count differs from manifest")
        # Validate the immutable evidence references before accepting any decisions.
        # Crop files are content-addressed; source PDFs are checked when their path is
        # present (the synthetic/unit-test index may intentionally omit it).
        if not validate_evidence:
            return records
        checked_pdfs: dict[str, str] = {}
        package_root = self.package_root.resolve()
        for number, record in enumerate(records, 1):
            for field in (
                "pdf_id",
                "format_id",
                "variable",
                "provisional_value",
                "source_pdf_sha256",
                "source_page",
                "panel_id",
                "bbox",
                "cell_crop_sha256",
                "selector",
                "scope",
            ):
                if field not in record:
                    raise SourceAuditError(f"verification index record {number} lacks {field}")
            source_pdf = record.get("source_pdf")
            if source_pdf:
                pdf_path = Path(str(source_pdf)).resolve()
                if not pdf_path.is_file():
                    raise SourceAuditError(f"source PDF is missing: {pdf_path}")
                expected_pdf_sha = str(record["source_pdf_sha256"]).upper()
                pdf_key = str(source_pdf)
                actual_pdf_sha = checked_pdfs.get(pdf_key)
                if actual_pdf_sha is None:
                    actual_pdf_sha = _sha256(pdf_path)
                    checked_pdfs[pdf_key] = actual_pdf_sha
                if actual_pdf_sha != expected_pdf_sha:
                    raise SourceAuditError(
                        f"source PDF hash differs for {record['pdf_id']}: "
                        f"{actual_pdf_sha} != {expected_pdf_sha}"
                    )
                if checked_pdfs[pdf_key] != expected_pdf_sha:
                    raise SourceAuditError(
                        f"inconsistent source PDF hash for {record['pdf_id']}"
                    )
            crop_name = record.get("cell_crop")
            if crop_name:
                crop_path = (package_root / str(crop_name)).resolve()
                if package_root not in crop_path.parents:
                    raise SourceAuditError("cell crop escapes the verification package")
                if not crop_path.is_file():
                    raise SourceAuditError(f"cell crop is missing: {crop_path}")
                actual_crop_sha = _sha256(crop_path)
                expected_crop_sha = str(record["cell_crop_sha256"]).upper()
                if actual_crop_sha != expected_crop_sha:
                    raise SourceAuditError(
                        f"cell crop hash differs for {record['pdf_id']} record {number}"
                    )
        return records

    @staticmethod
    def _load_decisions(path: Path) -> list[tuple[str, CellReview]]:
        decisions: list[tuple[str, CellReview]] = []
        for line_number, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
                pdf_id = str(payload.pop("pdf_id"))
                if payload.get("status") == "PENDING":
                    raise SourceAuditError(f"line {line_number} is still PENDING")
                decisions.append((pdf_id, CellReview.model_validate(payload)))
            except (KeyError, TypeError, json.JSONDecodeError) as exc:
                raise SourceAuditError(f"invalid decision at line {line_number}: {exc}") from exc
        return decisions

    @classmethod
    def _index_key(cls, item: dict[str, Any]) -> tuple[str, str, int, int | None, str]:
        selector = item["selector"]
        if "row_index" in selector:
            return (item["pdf_id"], "row", int(selector["row_index"]), None, item["variable"])
        return (
            item["pdf_id"],
            item["scope"],
            int(selector["parent_row_index"]),
            int(selector["subrow_index"]) if "subrow_index" in selector else None,
            item["variable"],
        )

    @classmethod
    def _review_key(cls, pdf_id: str, review: CellReview) -> tuple[str, str, int, int | None, str]:
        selector = review.selector.model_dump(mode="json", exclude_none=True)
        if "row_index" in selector:
            return (pdf_id, "row", int(selector["row_index"]), None, review.variable)
        return (
            pdf_id,
            review.scope,
            int(selector["parent_row_index"]),
            int(selector["subrow_index"]) if "subrow_index" in selector else None,
            review.variable,
        )

    @staticmethod
    def _sort_review(review: CellReview) -> tuple[int, int, str]:
        selector = review.selector
        if selector.row_index is not None:
            return (selector.row_index, -1, review.variable)
        return (
            selector.parent_row_index or 0,
            selector.subrow_index if selector.subrow_index is not None else -1,
            review.variable,
        )

    @staticmethod
    def _validate_immutable(pdf_id: str, review: CellReview, item: dict[str, Any]) -> None:
        selector = review.selector.model_dump(mode="json", exclude_none=True)
        checks = {
            "selector": selector == item["selector"],
            "scope": review.scope == item["scope"],
            "variable": review.variable == item["variable"],
            "original": review.expected_original == item["provisional_value"],
            "page": review.source_page == int(item["source_page"]),
            "panel": review.panel_id == item["panel_id"],
            "bbox": list(review.bbox) == item["bbox"],
            "crop": review.crop_sha256.upper() == item["cell_crop_sha256"],
            "evidence": str(review.evidence_sha256).upper() == item["cell_crop_sha256"],
        }
        if not all(checks.values()):
            failed = [name for name, valid in checks.items() if not valid]
            raise SourceAuditError(f"{pdf_id}: immutable source evidence differs: {failed}")
