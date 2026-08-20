"""Atomic run-scoped clean, quarantine, audit, and manifest exports."""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable, cast

import pandas as pd

from census_extractor.metadata import DocumentMetadata
from census_extractor.normalization import NormalizedRow
from census_extractor.schemas import TableSchema
from census_extractor.validation.validator import TableValidationReport


@dataclass(frozen=True, slots=True)
class RunLayout:
    root: Path
    clean: Path
    quarantine: Path
    audit: Path
    viz: Path
    manifest: Path

    @classmethod
    def create(cls, runs_dir: Path, run_id: str) -> "RunLayout":
        root = Path(runs_dir) / run_id
        layout = cls(
            root,
            root / "clean",
            root / "quarantine",
            root / "audit",
            root / "viz",
            root / "manifest.json",
        )
        for directory in (layout.clean, layout.quarantine, layout.audit, layout.viz):
            directory.mkdir(parents=True, exist_ok=True)
        return layout


class TableExporter:
    def __init__(self, layout: RunLayout):
        self.layout = layout

    def export_table(
        self,
        metadata: DocumentMetadata,
        schema: TableSchema,
        rows: list[NormalizedRow],
        report: TableValidationReport,
        status: str,
        source_pdf_sha256: str,
    ) -> dict[str, Path]:
        area = self.layout.clean if status == "SUCCESS" else self.layout.quarantine
        target = area / metadata.pdf_id
        target.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(UTC).isoformat()
        records: list[dict[str, Any]] = []
        for index, row in enumerate(rows):
            record = dict(row.values)
            record.update(
                {
                    "row_index": index,
                    "pdf_id": metadata.pdf_id,
                    "district": metadata.district,
                    "state": metadata.state,
                    "year": metadata.year,
                    "format_id": metadata.format_id,
                    "table_id": metadata.table_id,
                    "source_pdf": metadata.file_name,
                    "source_pdf_sha256": source_pdf_sha256,
                    "source_page_start": metadata.source_page_start,
                    "source_page_end": metadata.source_page_end,
                    "anchor_printed_page": metadata.anchor_printed_page,
                    "continuation_printed_page": metadata.continuation_printed_page,
                    "metadata_workbook": metadata.workbook_path,
                    "metadata_workbook_sha256": metadata.workbook_sha256,
                    "extracted_at": timestamp,
                }
            )
            records.append(record)

        ordered_schema = schema.get_all_variables()
        derived = ["pucca_road_km", "kutcha_road_km", "row_type", "reference_target"]
        provenance = [
            "row_index",
            "pdf_id",
            "district",
            "state",
            "year",
            "format_id",
            "table_id",
            "source_pdf",
            "source_pdf_sha256",
            "source_page_start",
            "source_page_end",
            "anchor_printed_page",
            "continuation_printed_page",
            "metadata_workbook",
            "metadata_workbook_sha256",
            "extracted_at",
        ]
        columns = [
            column
            for column in ordered_schema + derived + provenance
            if any(column in record for record in records)
        ]
        frame = pd.DataFrame(records).reindex(columns=columns)
        self._apply_schema_dtypes(frame, schema)
        paths = {
            "csv": target / "table.csv",
            "parquet": target / "table.parquet",
            "jsonl": target / "table.jsonl",
            "report": target / "validation.json",
        }
        self._atomic_dataframe_csv(frame, paths["csv"])
        self._atomic_dataframe_parquet(frame, paths["parquet"])
        self._atomic_jsonl(paths["jsonl"], records)
        self._atomic_json(
            paths["report"],
            {
                "table_name": report.table_name,
                "format_id": report.format_id,
                "status": status,
                "total_rows": report.total_rows,
                "valid_rows": report.valid_rows_count,
                "quality": {**asdict(report.quality), "overall": report.quality.overall},
                "quality_threshold": report.quality_threshold,
                "panels_complete": report.panels_complete,
                "alignment_complete": report.alignment_complete,
                "findings": [asdict(finding) for finding in report.findings],
            },
        )
        return paths

    @staticmethod
    def _apply_schema_dtypes(frame: pd.DataFrame, schema: TableSchema) -> None:
        for column in schema.get_all_columns():
            if column.variable not in frame:
                continue
            values = cast(pd.Series, frame[column.variable]).tolist()
            if column.data_type == "integer":
                frame[column.variable] = pd.array(values, dtype="Int64")
            elif column.data_type == "float":
                frame[column.variable] = pd.array(values, dtype="Float64")
            else:
                frame[column.variable] = pd.array(values, dtype="string")
        for variable in ("pucca_road_km", "kutcha_road_km"):
            if variable in frame:
                values = cast(pd.Series, frame[variable]).tolist()
                frame[variable] = pd.array(values, dtype="Float64")
        for variable in (
            "row_index",
            "year",
            "source_page_start",
            "source_page_end",
            "anchor_printed_page",
            "continuation_printed_page",
        ):
            if variable in frame:
                values = cast(pd.Series, frame[variable]).tolist()
                frame[variable] = pd.array(values, dtype="Int64")

    def write_audit(self, pdf_id: str, records: Iterable[dict[str, Any]]) -> Path:
        path = self.layout.audit / f"{pdf_id}.jsonl"
        self._atomic_jsonl(path, records)
        return path

    def write_geometry(self, pdf_id: str, payload: dict[str, Any]) -> Path:
        path = self.layout.audit / f"{pdf_id}.geometry.json"
        self._atomic_json(path, payload)
        return path

    @classmethod
    def write_manifest(cls, path: Path, payload: dict[str, Any]) -> None:
        cls._atomic_json(path, payload)

    @staticmethod
    def _temporary(path: Path) -> Path:
        return path.with_name(f".{path.name}.{time.time_ns()}.tmp")

    @classmethod
    def _atomic_dataframe_csv(cls, frame: pd.DataFrame, path: Path) -> None:
        temporary = cls._temporary(path)
        frame.to_csv(temporary, index=False, encoding="utf-8")
        temporary.replace(path)

    @classmethod
    def _atomic_dataframe_parquet(cls, frame: pd.DataFrame, path: Path) -> None:
        temporary = cls._temporary(path)
        frame.to_parquet(temporary, index=False, engine="pyarrow")
        temporary.replace(path)

    @classmethod
    def _atomic_jsonl(cls, path: Path, records: Iterable[dict[str, Any]]) -> None:
        temporary = cls._temporary(path)
        with temporary.open("w", encoding="utf-8", newline="\n") as handle:
            for record in records:
                handle.write(
                    json.dumps(record, ensure_ascii=False, default=str, sort_keys=True) + "\n"
                )
        temporary.replace(path)

    @classmethod
    def _atomic_json(cls, path: Path, payload: dict[str, Any]) -> None:
        temporary = cls._temporary(path)
        temporary.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False, default=str, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        temporary.replace(path)
