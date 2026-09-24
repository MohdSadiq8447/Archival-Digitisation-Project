"""Immutable crop and lineage package for the later Codex source audit."""

from __future__ import annotations

import hashlib
import io
import json
import shutil
import uuid
from pathlib import Path
from typing import Any

import pandas as pd
from PIL import Image

from census_extractor.autocorrection import (
    AutomaticDecisionLedger,
    AutomaticTranscriptionCorrector,
    enumerate_unique_cells,
    sha256_file,
)
from census_extractor.config import PipelineConfig
from census_extractor.metadata import DocumentMetadata
from census_extractor.preprocessing.pdf_loader import PDFLoader
from census_extractor.schemas import SchemaRegistry


class CodexVerificationPackageBuilder:
    """Create 300-DPI panel, row, and cell evidence without an Excel workflow."""

    def __init__(self, config: PipelineConfig):
        self.config = config
        self.schemas = SchemaRegistry(config.schemas_dir)
        self.loader = PDFLoader(target_dpi=300, auto_deskew=config.auto_deskew)

    def build(
        self,
        *,
        source_manifest: Path,
        automatic_ledger: Path,
        provisional_root: Path,
        documents: list[DocumentMetadata],
    ) -> dict[str, Any]:
        source_manifest = Path(source_manifest).resolve()
        automatic_ledger = Path(automatic_ledger).resolve()
        provisional_root = Path(provisional_root).resolve()
        package_root = provisional_root / "codex_verification"
        manifest_hash = sha256_file(source_manifest)
        ledger_hash = sha256_file(automatic_ledger)
        if package_root.is_dir():
            return self._validate_existing(
                package_root, manifest_hash, ledger_hash, len(documents)
            )

        extraction = json.loads(source_manifest.read_text(encoding="utf-8"))
        results = extraction.get("results", {})
        ledger = AutomaticDecisionLedger.load(automatic_ledger)
        if ledger.version < 2 or ledger.verification_strategy != "full_cell_consensus":
            raise ValueError("Codex package requires a full-cell automatic decision ledger")
        if ledger.source_manifest_sha256 != manifest_hash:
            raise ValueError("automatic ledger does not match the extraction manifest")

        temporary = package_root.with_name(
            f".{package_root.name}.{uuid.uuid4().hex}.tmp"
        )
        temporary.mkdir(parents=True)
        index_path = temporary / "verification_index.jsonl"
        record_count = 0
        try:
            with index_path.open("w", encoding="utf-8", newline="\n") as handle:
                for document in documents:
                    record_count += self._write_document_records(
                        handle,
                        temporary,
                        document,
                        results.get(document.pdf_id),
                        ledger,
                        provisional_root,
                        manifest_hash,
                    )
            index_hash = sha256_file(index_path)
            package_manifest = {
                "version": 1,
                "purpose": "codex_source_audit",
                "render_dpi": 300,
                "source_manifest_sha256": manifest_hash,
                "automatic_ledger_sha256": ledger_hash,
                "verification_index": "verification_index.jsonl",
                "verification_index_sha256": index_hash,
                "selected_pdfs": len(documents),
                "unique_source_cells": record_count,
                "human_review_workbook": False,
            }
            (temporary / "verification_manifest.json").write_text(
                json.dumps(package_manifest, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
                newline="\n",
            )
            temporary.replace(package_root)
        except Exception:
            shutil.rmtree(temporary, ignore_errors=True)
            raise
        return {
            "root": str(package_root),
            "index": str(package_root / "verification_index.jsonl"),
            "index_sha256": index_hash,
            "unique_source_cells": record_count,
            "selected_pdfs": len(documents),
        }

    def _write_document_records(
        self,
        handle: Any,
        temporary: Path,
        document: DocumentMetadata,
        extraction_record: dict[str, Any] | None,
        ledger: AutomaticDecisionLedger,
        provisional_root: Path,
        source_manifest_hash: str,
    ) -> int:
        if extraction_record is None or document.pdf_id not in ledger.tables:
            raise ValueError(f"{document.pdf_id}: missing extraction or automatic lineage")
        csv_path = provisional_root / "csv" / f"{document.pdf_id}.csv"
        geometry_path = Path(
            extraction_record.get("exported_files", {}).get("geometry", "")
        )
        pdf_path = self.config.pdfs_dir / document.file_name
        if not csv_path.is_file() or not geometry_path.is_file() or not pdf_path.is_file():
            raise FileNotFoundError(f"{document.pdf_id}: verification input is missing")
        frame = pd.read_csv(csv_path, dtype=str, keep_default_na=False)
        schema = self.schemas.require(document.format_id)
        geometry = json.loads(geometry_path.read_text(encoding="utf-8"))
        pages = self.loader.render_pdf(pdf_path)
        decisions = {
            self._decision_key(item): item
            for item in ledger.tables[document.pdf_id].decisions
        }
        cells = enumerate_unique_cells(frame, schema)
        if len(decisions) != len(cells):
            raise ValueError(f"{document.pdf_id}: automatic decision coverage is incomplete")
        panel_files: dict[str, tuple[str, str]] = {}
        row_files: dict[tuple[str, str], tuple[str, str]] = {}
        count = 0
        for cell in cells:
            column = schema.get_column_by_var(cell.variable)
            if column is None:
                raise ValueError(f"{document.pdf_id}: unknown variable {cell.variable}")
            definition = next(
                panel for panel in schema.panels if column.column_no in panel.printed_columns
            )
            panel = next(
                item for item in geometry["panels"] if item["panel_id"] == definition.panel_id
            )
            page = pages[int(panel["page"]) - 1]
            cell_bbox = AutomaticTranscriptionCorrector._clip_bbox(
                AutomaticTranscriptionCorrector._cell_bbox(
                    panel, schema, column, cell.selector
                ),
                page,
            )
            row_bbox = AutomaticTranscriptionCorrector._clip_bbox(
                AutomaticTranscriptionCorrector._row_bbox(
                    panel, schema, column, cell.selector
                ),
                page,
            )
            selector_name = self._selector_name(cell)
            panel_file = panel_files.get(definition.panel_id)
            if panel_file is None:
                table_bbox = panel["table_bbox"]
                panel_bbox = (
                    int(table_bbox[0]),
                    int(table_bbox[1]),
                    int(table_bbox[2]),
                    int(table_bbox[3]),
                )
                panel_file = self._save_crop(
                    temporary,
                    Path("crops")
                    / document.pdf_id
                    / "panels"
                    / f"{definition.panel_id}-p{page.page_number}.png",
                    page.image.crop(panel_bbox),
                )
                panel_files[definition.panel_id] = panel_file
            row_key = (definition.panel_id, selector_name)
            row_file = row_files.get(row_key)
            if row_file is None:
                row_file = self._save_crop(
                    temporary,
                    Path("crops")
                    / document.pdf_id
                    / "rows"
                    / f"{selector_name}-{definition.panel_id}.png",
                    page.image.crop(row_bbox),
                )
                row_files[row_key] = row_file
            cell_file = self._save_crop(
                temporary,
                Path("crops")
                / document.pdf_id
                / "cells"
                / f"{selector_name}-{cell.variable}.png",
                page.image.crop(cell_bbox),
            )
            key = cell.key
            decision = decisions.get(key)
            if decision is None:
                raise ValueError(f"{document.pdf_id}: missing decision for {key}")
            flags = sorted(
                {
                    str(frame.at[index, f"{cell.variable}_flag"]).strip()
                    for index in cell.frame_indices
                    if str(frame.at[index, f"{cell.variable}_flag"]).strip()
                }
            )
            output = {
                "pdf_id": document.pdf_id,
                "district": document.district,
                "format_id": document.format_id,
                "source_pdf": str(pdf_path),
                "source_pdf_sha256": sha256_file(pdf_path),
                "source_manifest_sha256": source_manifest_hash,
                "geometry_sha256": sha256_file(geometry_path),
                "selector": cell.selector.model_dump(mode="json", exclude_none=True),
                "scope": cell.scope,
                "variable": cell.variable,
                "provisional_value": cell.original,
                "provisional_flags": flags,
                "requires_review": decision.status == "UNRESOLVED",
                "source_page": page.page_number,
                "panel_id": definition.panel_id,
                "bbox": list(cell_bbox),
                "panel_crop": panel_file[0],
                "panel_crop_sha256": panel_file[1],
                "row_crop": row_file[0],
                "row_crop_sha256": row_file[1],
                "cell_crop": cell_file[0],
                "cell_crop_sha256": cell_file[1],
                "novita_decision": decision.model_dump(mode="json"),
            }
            handle.write(json.dumps(output, ensure_ascii=False, sort_keys=True) + "\n")
            count += 1
        return count

    @staticmethod
    def _decision_key(decision: Any) -> tuple[str, int, int | None, str]:
        selector = decision.selector
        if selector.row_index is not None:
            return ("row", selector.row_index, None, decision.variable)
        return (
            decision.scope,
            selector.parent_row_index,
            selector.subrow_index,
            decision.variable,
        )

    @staticmethod
    def _selector_name(cell: Any) -> str:
        selector = cell.selector
        if selector.row_index is not None:
            return f"r{selector.row_index:04d}"
        value = f"p{selector.parent_row_index:04d}"
        if selector.subrow_index is not None:
            value += f"-s{selector.subrow_index:03d}"
        return value

    @staticmethod
    def _save_crop(root: Path, relative: Path, image: Image.Image) -> tuple[str, str]:
        destination = root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        buffer = io.BytesIO()
        image.convert("RGB").save(buffer, format="PNG", optimize=False)
        payload = buffer.getvalue()
        destination.write_bytes(payload)
        return relative.as_posix(), hashlib.sha256(payload).hexdigest().upper()

    @staticmethod
    def _validate_existing(
        root: Path, manifest_hash: str, ledger_hash: str, expected_pdfs: int
    ) -> dict[str, Any]:
        manifest_path = root / "verification_manifest.json"
        index_path = root / "verification_index.jsonl"
        if not manifest_path.is_file() or not index_path.is_file():
            raise ValueError("existing Codex verification package is incomplete")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("source_manifest_sha256") != manifest_hash:
            raise ValueError("existing verification package has a stale source manifest")
        if manifest.get("automatic_ledger_sha256") != ledger_hash:
            raise ValueError("existing verification package has a stale automatic ledger")
        if manifest.get("verification_index_sha256") != sha256_file(index_path):
            raise ValueError("existing verification index hash differs from its manifest")
        if int(manifest.get("selected_pdfs", -1)) != expected_pdfs:
            raise ValueError("existing verification package PDF scope differs")
        return {
            "root": str(root),
            "index": str(index_path),
            "index_sha256": manifest["verification_index_sha256"],
            "unique_source_cells": int(manifest["unique_source_cells"]),
            "selected_pdfs": expected_pdfs,
        }
