"""Resumable, IDE-friendly automatic workflow for the remaining UP archive."""

from __future__ import annotations

import asyncio
import csv
import hashlib
import json
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

import pandas as pd
import yaml
from pydantic import BaseModel, Field, model_validator

from census_extractor.autocorrection import AutomaticTranscriptionCorrector, sha256_file
from census_extractor.config import PipelineConfig
from census_extractor.metadata import DocumentMetadata, MetadataRegistry
from census_extractor.pipeline.runner import PipelineRunner
from census_extractor.postprocessing import CSVPostprocessor
from census_extractor.schemas import SchemaRegistry, TableSchema
from census_extractor.verification import CodexVerificationPackageBuilder

FORMAT_FILE_ORDER = {
    "format_001": "civic",
    "format_002": "mededu",
    "format_003": "tehsil",
}
STRUCTURAL_FINDING_CODES = {
    "panel_discovery",
    "row_count",
    "panel_alignment",
    "hierarchy_lineage",
    "hierarchy_parent_sequence",
    "hierarchy_subrow_sequence",
    "hierarchy_identity",
    "hierarchy_parent_values",
}


class WorkflowSettings(BaseModel):
    version: int = Field(default=3, ge=3)
    workflow_id: str
    geometry_run_id: str
    extraction_run_id: str
    postprocess_output_id: str
    excluded_districts: list[str]
    expected_district_count: int = Field(ge=1)
    expected_pdf_count: int = Field(ge=1)
    expected_format_counts: dict[str, int]
    format_order: list[str] = Field(default_factory=lambda: list(FORMAT_FILE_ORDER))
    pdf_concurrency: int = Field(default=1, ge=1, le=1)
    request_concurrency: int = Field(default=1, ge=1, le=1)
    max_cell_retries: int = Field(default=2, ge=1, le=2)
    transcription_temperature: float = Field(default=0.0, ge=0.0, le=2.0)
    uncertain_policy: Literal["keep_value_and_flag"] = "keep_value_and_flag"
    hard_failure_policy: Literal["block_and_resume"] = "block_and_resume"
    generate_review_workbook: Literal[False] = False
    import_extraction_run_ids: list[str] = Field(default_factory=list)
    generate_codex_verification_package: Literal[True] = True

    @model_validator(mode="after")
    def validate_settings(self) -> "WorkflowSettings":
        identifiers = {
            self.workflow_id,
            self.geometry_run_id,
            self.extraction_run_id,
            self.postprocess_output_id,
        }
        if len(identifiers) != 4 or any(Path(value).name != value for value in identifiers):
            raise ValueError("workflow and run identifiers must be distinct directory names")
        if set(self.format_order) != set(FORMAT_FILE_ORDER):
            raise ValueError("format_order must contain format_001, format_002, and format_003")
        if set(self.expected_format_counts) != set(FORMAT_FILE_ORDER):
            raise ValueError("expected_format_counts must cover all three formats")
        if any(Path(value).name != value for value in self.import_extraction_run_ids):
            raise ValueError("import extraction run ids must be directory names")
        return self

    @classmethod
    def load(cls, path: Path) -> "WorkflowSettings":
        with Path(path).open("r", encoding="utf-8") as handle:
            return cls.model_validate(yaml.safe_load(handle))


@dataclass(frozen=True, slots=True)
class WorkflowResult:
    status: str
    message: str
    state_path: Path
    review_workbook: Path | None = None
    final_output: Path | None = None


class RemainingUPWorkflow:
    """Run geometry, extraction, automatic correction, post-processing, and merging."""

    def __init__(self, config: PipelineConfig, settings_path: Path):
        self.settings_path = Path(settings_path).resolve()
        self.settings = WorkflowSettings.load(self.settings_path)
        self.config = config.with_overrides(
            global_concurrency=1,
            transcription_temperature=self.settings.transcription_temperature,
        )
        self.metadata = MetadataRegistry(self.config.metadata_path)
        self.schemas = SchemaRegistry(self.config.schemas_dir)
        self.workflow_root = self.config.outputs_dir / "workflows" / self.settings.workflow_id
        self.state_path = self.workflow_root / "workflow.json"
        self.automatic_root = self.workflow_root / "automatic"
        self.decision_root = self.automatic_root / "decisions"
        self.automatic_ledger = self.automatic_root / "automatic_decisions.yaml"
        self.final_root = (
            self.config.outputs_dir / "postprocessed" / self.settings.postprocess_output_id
        )
        self.verification_root = self.final_root / "codex_verification"
        self.documents = self.select_documents()
        self._config_sha = sha256_file(self.settings_path)
        self._metadata_sha = self.metadata.workbook_sha256.upper()
        self._selection_sha = hashlib.sha256(
            "\n".join(document.pdf_id for document in self.documents).encode("utf-8")
        ).hexdigest().upper()

    def select_documents(self) -> list[DocumentMetadata]:
        excluded = {district.casefold() for district in self.settings.excluded_districts}
        rank = {format_id: index for index, format_id in enumerate(self.settings.format_order)}
        documents = [
            document
            for document in self.metadata.all()
            if document.district.casefold() not in excluded
        ]
        documents.sort(key=lambda item: (item.district.casefold(), rank[item.format_id]))
        districts = {document.district.casefold() for document in documents}
        counts = {
            format_id: sum(document.format_id == format_id for document in documents)
            for format_id in self.settings.format_order
        }
        missing_files = [
            document.file_name
            for document in documents
            if not (self.config.pdfs_dir / document.file_name).is_file()
        ]
        if len(districts) != self.settings.expected_district_count:
            raise ValueError(
                f"Selected {len(districts)} districts; expected "
                f"{self.settings.expected_district_count}"
            )
        if len(documents) != self.settings.expected_pdf_count:
            raise ValueError(
                f"Selected {len(documents)} PDFs; expected {self.settings.expected_pdf_count}"
            )
        if counts != self.settings.expected_format_counts:
            raise ValueError(
                f"Selected format counts {counts}; expected {self.settings.expected_format_counts}"
            )
        if missing_files:
            raise FileNotFoundError(f"Selected PDFs are missing: {missing_files}")
        return documents

    def run(self) -> WorkflowResult:
        state = self._load_or_create_state()
        if state["stage"] == "PROVISIONAL_COMPLETE":
            return WorkflowResult(
                state["stage"],
                "Provisional workflow is already complete; no OCR or output work was repeated.",
                self.state_path,
                final_output=self.final_root,
            )

        geometry_blockers = self._run_geometry_stage(state)
        if geometry_blockers:
            return self._blocked_result(
                state,
                "BLOCKED_GEOMETRY",
                geometry_blockers,
                "Geometry preflight is incomplete; fix the listed PDFs and rerun.",
            )

        extraction_blockers = self._run_extraction_stage(state, self.documents)
        if extraction_blockers:
            return self._blocked_result(
                state,
                "BLOCKED_EXTRACTION",
                extraction_blockers,
                "Paid extraction is incomplete; failed PDFs remain resumable.",
            )

        extraction_manifest = self.config.runs_dir / self.settings.extraction_run_id / "manifest.json"
        automatic = asyncio.run(
            AutomaticTranscriptionCorrector(
                self.config,
                max_cell_retries=self.settings.max_cell_retries,
            ).run_async(
                manifest_path=extraction_manifest,
                documents=self.documents,
                decision_root=self.decision_root,
            )
        )
        state["automatic_correction"] = {
            "ledger": str(automatic.ledger_path),
            "ledger_sha256": sha256_file(automatic.ledger_path),
            "included": len(automatic.included_pdf_ids),
            "corrected_cells": automatic.corrected_cells,
            "confirmed_cells": automatic.confirmed_cells,
            "unresolved_cells": automatic.unresolved_cells,
            "cache_hits": automatic.cache_hits,
            "cache_misses": automatic.cache_misses,
            "failures": automatic.exclusions,
        }
        if automatic.exclusions or set(automatic.included_pdf_ids) != {
            item.pdf_id for item in self.documents
        }:
            return self._blocked_result(
                state,
                "BLOCKED_NOVITA_VERIFICATION",
                automatic.exclusions,
                "Full-cell Novita verification is incomplete; rerun to resume.",
            )
        state["stage"] = "NOVITA_VERIFIED"
        self._save_state(state)

        if not self.final_root.exists():
            result = CSVPostprocessor(self.config).run_automatic(
                source_run=self.settings.extraction_run_id,
                ledger_path=self.automatic_ledger,
                output_id=self.settings.postprocess_output_id,
            )
            state["postprocess"] = {
                "output": str(result.output_root),
                "csv_count": len(result.csv_files),
                "automatic_decisions": result.reviewed_unique_cells,
                "correction_entries": result.corrected_cells,
                "unresolved_cells": result.unresolved_cells,
            }
        else:
            self._validate_existing_postprocess(extraction_manifest, self.documents)
            state.setdefault(
                "postprocess",
                {
                    "output": str(self.final_root),
                    "csv_count": len(self.documents),
                    "automatic_decisions": state["automatic_correction"]["corrected_cells"]
                    + state["automatic_correction"]["confirmed_cells"]
                    + state["automatic_correction"]["unresolved_cells"],
                    "correction_entries": state["automatic_correction"]["corrected_cells"],
                    "unresolved_cells": state["automatic_correction"]["unresolved_cells"],
                },
            )
        state["stage"] = "POSTPROCESSED_PROVISIONAL"
        self._save_state(state)

        merge_summary = self._merge_outputs(self.documents)
        verification = CodexVerificationPackageBuilder(self.config).build(
            source_manifest=extraction_manifest,
            automatic_ledger=self.automatic_ledger,
            provisional_root=self.final_root,
            documents=self.documents,
        )
        report_path = self._write_workflow_report(state, merge_summary, [], "PROVISIONAL_COMPLETE")
        state["merge"] = merge_summary
        state["codex_verification_package"] = verification
        state["workflow_report"] = str(report_path)
        state["stage"] = "PROVISIONAL_COMPLETE"
        state["completed_at"] = datetime.now(UTC).isoformat()
        self._save_state(state)
        return WorkflowResult(
            "PROVISIONAL_COMPLETE",
            "Novita verification and provisional post-processing completed for all 142 PDFs.",
            self.state_path,
            final_output=self.final_root,
        )

    def _run_geometry_stage(self, state: dict[str, Any]) -> list[dict[str, str]]:
        manifest_path = self.config.runs_dir / self.settings.geometry_run_id / "manifest.json"
        existing = self._manifest_results(manifest_path)
        self._guard_manifest_scope(existing)
        pending = [
            document
            for document in self.documents
            if existing.get(document.pdf_id, {}).get("status") != "DRY_RUN"
        ]
        if pending:
            runner = PipelineRunner(
                self.config,
                run_id=self.settings.geometry_run_id,
                resume=manifest_path.is_file(),
            )
            asyncio.run(self._process_documents_sequentially(runner, pending, is_dry_run=True))
        results = self._manifest_results(manifest_path)
        blockers = [
            {
                "pdf_id": document.pdf_id,
                "reason": str(results.get(document.pdf_id, {}).get("error_message") or "missing"),
            }
            for document in self.documents
            if results.get(document.pdf_id, {}).get("status") != "DRY_RUN"
        ]
        state["geometry"] = {
            "run_id": self.settings.geometry_run_id,
            "manifest": str(manifest_path),
            "manifest_sha256": sha256_file(manifest_path) if manifest_path.is_file() else None,
            "completed": len(self.documents) - len(blockers),
            "blockers": blockers,
        }
        state["stage"] = "GEOMETRY_COMPLETE"
        self._save_state(state)
        return blockers

    def _run_extraction_stage(
        self,
        state: dict[str, Any],
        documents: list[DocumentMetadata] | None = None,
    ) -> list[dict[str, str]]:
        documents = list(self.documents if documents is None else documents)
        manifest_path = self.config.runs_dir / self.settings.extraction_run_id / "manifest.json"
        self._import_extraction_results(manifest_path, documents)
        existing = self._manifest_results(manifest_path)
        self._guard_manifest_scope(existing)
        pending = [
            document
            for document in documents
            if not self._is_reviewable_result(existing.get(document.pdf_id))
        ]
        if pending:
            if not self.config.is_novita_configured:
                raise ValueError(
                    "NOVITA_API_KEY is required for the live extraction stage after geometry"
                )
            runner = PipelineRunner(
                self.config,
                run_id=self.settings.extraction_run_id,
                resume=manifest_path.is_file(),
            )
            asyncio.run(self._process_documents_sequentially(runner, pending, is_dry_run=False))
        results = self._manifest_results(manifest_path)
        blockers = [
            {
                "pdf_id": document.pdf_id,
                "reason": self._blocking_reason(results.get(document.pdf_id)),
            }
            for document in documents
            if not self._is_reviewable_result(results.get(document.pdf_id))
        ]
        state["extraction"] = {
            "run_id": self.settings.extraction_run_id,
            "manifest": str(manifest_path),
            "manifest_sha256": sha256_file(manifest_path) if manifest_path.is_file() else None,
            "completed": len(documents) - len(blockers),
            "blockers": blockers,
        }
        state["stage"] = "EXTRACTION_COMPLETE"
        self._save_state(state)
        return blockers

    def _import_extraction_results(
        self, destination_manifest: Path, documents: list[DocumentMetadata]
    ) -> None:
        """Reuse paid artifacts only after source, schema, geometry, and row guards pass."""
        if destination_manifest.is_file():
            destination = json.loads(destination_manifest.read_text(encoding="utf-8"))
        else:
            destination = {
                "run_id": self.settings.extraction_run_id,
                "created_at": datetime.now(UTC).isoformat(),
                "novita_model": self.config.novita_model,
                "prompt_version": self.config.prompt_version,
                "transcription_temperature": self.config.transcription_temperature,
                "quality_threshold": self.config.quality_threshold,
                "results": {},
            }
        destination_results = destination.setdefault("results", {})
        wanted = {document.pdf_id: document for document in documents}
        geometry_manifest = (
            self.config.runs_dir / self.settings.geometry_run_id / "manifest.json"
        )
        geometry_results = self._manifest_results(geometry_manifest)
        imported = False
        for run_id in self.settings.import_extraction_run_ids:
            source_manifest = self.config.runs_dir / run_id / "manifest.json"
            if not source_manifest.is_file():
                continue
            source_hash = sha256_file(source_manifest)
            source_results = self._manifest_results(source_manifest)
            for pdf_id, record in source_results.items():
                if pdf_id not in wanted or pdf_id in destination_results:
                    continue
                if not self._valid_imported_result(
                    wanted[pdf_id], record, geometry_results.get(pdf_id)
                ):
                    continue
                imported_record = dict(record)
                imported_record["imported_from_run"] = run_id
                imported_record["imported_manifest_sha256"] = source_hash
                destination_results[pdf_id] = imported_record
                imported = True
        if imported or not destination_manifest.is_file():
            destination_manifest.parent.mkdir(parents=True, exist_ok=True)
            self._atomic_json(destination_manifest, destination)

    def _valid_imported_result(
        self,
        document: DocumentMetadata,
        record: dict[str, Any],
        geometry_record: dict[str, Any] | None,
    ) -> bool:
        try:
            if not self._is_reviewable_result(record) or geometry_record is None:
                return False
            if record.get("format_id") != document.format_id:
                return False
            exported = record.get("exported_files", {})
            csv_path = Path(exported.get("csv", ""))
            old_geometry_path = Path(exported.get("geometry", ""))
            new_geometry_path = Path(
                geometry_record.get("exported_files", {}).get("geometry", "")
            )
            if not all(path.is_file() for path in (csv_path, old_geometry_path, new_geometry_path)):
                return False
            source_hash = sha256_file(self.config.pdfs_dir / document.file_name)
            old_geometry = json.loads(old_geometry_path.read_text(encoding="utf-8"))
            new_geometry = json.loads(new_geometry_path.read_text(encoding="utf-8"))
            if {
                str(old_geometry.get("source_pdf_sha256", "")).upper(),
                str(new_geometry.get("source_pdf_sha256", "")).upper(),
            } != {source_hash}:
                return False
            schema = self.schemas.require(document.format_id)
            expected_panels = {panel.panel_id for panel in schema.panels}
            old_panels = {panel["panel_id"]: panel for panel in old_geometry.get("panels", [])}
            new_panels = {panel["panel_id"]: panel for panel in new_geometry.get("panels", [])}
            if set(old_panels) != expected_panels or set(new_panels) != expected_panels:
                return False
            if any(
                int(old_panels[key].get("row_count", -1))
                != int(new_panels[key].get("row_count", -2))
                for key in expected_panels
            ):
                return False
            if int(record.get("parent_rows", -1)) != int(
                geometry_record.get("parent_rows", -2)
            ) or int(record.get("total_rows", -1)) != int(
                geometry_record.get("total_rows", -2)
            ):
                return False
            frame = pd.read_csv(csv_path, dtype=str, keep_default_na=False)
            if len(frame) != int(record.get("total_rows", -1)):
                return False
            if not set(schema.get_all_variables()).issubset(frame.columns):
                return False
            if frame["row_index"].astype(int).tolist() != list(range(len(frame))):
                return False
            if schema.hierarchy is not None:
                if frame["parent_row_index"].nunique() != int(record.get("parent_rows", -1)):
                    return False
                for _, group in frame.groupby("parent_row_index", sort=True):
                    indexes = group["subrow_index"].astype(int).tolist()
                    if indexes != list(range(len(group))):
                        return False
                    if set(group["subrow_count"].astype(int)) != {len(group)}:
                        return False
            return True
        except (OSError, ValueError, KeyError, json.JSONDecodeError):
            return False

    async def _process_documents_sequentially(
        self,
        runner: PipelineRunner,
        documents: list[DocumentMetadata],
        *,
        is_dry_run: bool,
    ) -> None:
        try:
            for document in documents:
                await runner.process_pdf_async(
                    self.config.pdfs_dir / document.file_name,
                    save_viz=True,
                    is_dry_run=is_dry_run,
                )
        finally:
            await runner.ocr_client.aclose()

    @classmethod
    def _is_reviewable_result(cls, record: dict[str, Any] | None) -> bool:
        if not record or record.get("status") not in {"SUCCESS", "QUARANTINED"}:
            return False
        if record.get("status") == "SUCCESS":
            return True
        report_path = record.get("exported_files", {}).get("report")
        if not report_path or not Path(report_path).is_file():
            return False
        report = json.loads(Path(report_path).read_text(encoding="utf-8"))
        if not report.get("panels_complete") or not report.get("alignment_complete"):
            return False
        return not any(
            finding.get("severity") == "ERROR"
            and finding.get("code") in STRUCTURAL_FINDING_CODES
            for finding in report.get("findings", [])
        )

    @classmethod
    def _blocking_reason(cls, record: dict[str, Any] | None) -> str:
        if not record:
            return "missing extraction result"
        if record.get("status") == "ERROR":
            return str(record.get("error_message") or "operational ERROR")
        report_path = record.get("exported_files", {}).get("report")
        if report_path and Path(report_path).is_file():
            report = json.loads(Path(report_path).read_text(encoding="utf-8"))
            messages = [
                finding.get("message", finding.get("code", "structural finding"))
                for finding in report.get("findings", [])
                if finding.get("severity") == "ERROR"
                and finding.get("code") in STRUCTURAL_FINDING_CODES
            ]
            if messages:
                return "; ".join(messages[:5])
        return f"unusable status {record.get('status')!r}"

    def _merge_outputs(
        self,
        included_documents: list[DocumentMetadata] | None = None,
    ) -> dict[str, Any]:
        included = list(self.documents if included_documents is None else included_documents)
        csv_root = self.final_root / "csv"
        merge_root = self.final_root / "merged"
        merge_root.mkdir(parents=True, exist_ok=True)
        summary: dict[str, Any] = {}
        for format_id in self.settings.format_order:
            documents = [document for document in included if document.format_id == format_id]
            destination = merge_root / f"{format_id}_{FORMAT_FILE_ORDER[format_id]}.csv"
            temporary = destination.with_name(f".{destination.name}.{time.time_ns()}.tmp")
            header: list[str] | None = None
            row_count = 0
            with temporary.open("w", encoding="utf-8", newline="") as output_handle:
                writer: csv.DictWriter[str] | None = None
                for document in documents:
                    source = csv_root / f"{document.pdf_id}.csv"
                    if not source.is_file():
                        raise FileNotFoundError(f"Corrected CSV not found: {source}")
                    with source.open("r", encoding="utf-8", newline="") as input_handle:
                        reader = csv.DictReader(input_handle)
                        current_header = list(reader.fieldnames or [])
                        if header is None:
                            header = current_header
                            writer = csv.DictWriter(
                                output_handle, fieldnames=header, lineterminator="\n"
                            )
                            writer.writeheader()
                        elif current_header != header:
                            raise ValueError(f"Header mismatch while merging {source.name}")
                        assert writer is not None
                        for row in reader:
                            if row.get("pdf_id") != document.pdf_id:
                                raise ValueError(f"Unexpected pdf_id in {source.name}")
                            writer.writerow(row)
                            row_count += 1
                if header is None:
                    header = self._schema_header(self.schemas.require(format_id))
                    writer = csv.DictWriter(output_handle, fieldnames=header, lineterminator="\n")
                    writer.writeheader()
            temporary.replace(destination)
            summary[format_id] = {
                "source_csvs": len(documents),
                "rows": row_count,
                "path": str(destination),
                "sha256": sha256_file(destination),
            }
        return summary

    @staticmethod
    def _schema_header(schema: TableSchema) -> list[str]:
        fields = [
            field
            for variable in schema.get_all_variables()
            for field in (variable, f"{variable}_flag")
        ]
        if schema.format_id == "format_001":
            fields.extend(["pucca_road_km", "kutcha_road_km"])
        fields.extend(["row_type", "reference_target", "requires_review"])
        if schema.hierarchy is not None:
            fields.extend(["parent_row_index", "subrow_index", "subrow_count"])
        fields.extend(
            [
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
        )
        return fields

    def _validate_existing_postprocess(
        self,
        extraction_manifest: Path,
        included_documents: list[DocumentMetadata],
    ) -> None:
        expected_files = {f"{document.pdf_id}.csv" for document in included_documents}
        csv_root = self.final_root / "csv"
        actual_files = {path.name for path in csv_root.glob("*.csv")} if csv_root.is_dir() else set()
        if actual_files != expected_files:
            raise ValueError(
                "Existing automatic post-processing output does not match eligible scope: "
                f"missing={sorted(expected_files - actual_files)}, "
                f"extra={sorted(actual_files - expected_files)}"
            )
        for required in (
            "CORRECTION_LOG.csv",
            "UNRESOLVED_CELLS.csv",
            "POSTPROCESSING_REPORT.md",
            "AUTOMATIC_PROCESSING_REPORT.md",
        ):
            if not (self.final_root / required).is_file():
                raise ValueError(f"Existing post-processing output is missing {required}")
        report = (self.final_root / "POSTPROCESSING_REPORT.md").read_text(encoding="utf-8")
        if sha256_file(extraction_manifest) not in report:
            raise ValueError("Existing post-processing output belongs to another manifest")

    def _write_excluded_pdfs(self, exclusions: list[dict[str, str]]) -> Path:
        path = self.final_root / "EXCLUDED_PDFS.csv"
        temporary = path.with_name(f".{path.name}.{time.time_ns()}.tmp")
        with temporary.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=["pdf_id", "stage", "reason"],
                lineterminator="\n",
            )
            writer.writeheader()
            writer.writerows(exclusions)
        temporary.replace(path)
        return path

    def _write_workflow_report(
        self,
        state: dict[str, Any],
        merge_summary: dict[str, Any],
        exclusions: list[dict[str, str]],
        final_status: str,
    ) -> Path:
        path = self.final_root / "WORKFLOW_QA_REPORT.md"
        automatic = state.get("automatic_correction", {})
        lines = [
            "# Remaining Uttar Pradesh Novita Provisional Workflow QA",
            "",
            f"- Status: `{final_status}`",
            f"- Workflow: `{self.settings.workflow_id}`",
            f"- Selected districts: {self.settings.expected_district_count}",
            f"- Selected PDFs: {self.settings.expected_pdf_count}",
            f"- Geometry blockers: {len(state.get('geometry', {}).get('blockers', []))}",
            f"- Extraction blockers: {len(state.get('extraction', {}).get('blockers', []))}",
            f"- Automatically corrected cells: {automatic.get('corrected_cells', 0)}",
            f"- Automatically confirmed cells: {automatic.get('confirmed_cells', 0)}",
            f"- Unresolved cells retained and flagged: {automatic.get('unresolved_cells', 0)}",
            "- Excluded PDFs: 0 (the workflow blocks and resumes instead)",
            f"- Strict-cell cache hits: {automatic.get('cache_hits', 0)}",
            f"- Strict-cell cache misses: {automatic.get('cache_misses', 0)}",
            "- Human review workbook generated: no",
            "",
            "## Merged outputs",
            "",
            "| Format | Included source CSVs | Rows | File |",
            "|---|---:|---:|---|",
        ]
        for format_id in self.settings.format_order:
            item = merge_summary[format_id]
            lines.append(
                f"| `{format_id}` | {item['source_csvs']} | {item['rows']} | "
                f"`merged/{Path(item['path']).name}` |"
            )
        lines.extend(
            [
                "",
                "These files are provisional Novita outputs, not Codex source-verified final "
                "data. Every unique source cell received an independent row/panel reading; a "
                "strict enlarged cell crop was used on disagreement. Changes require agreement "
                "between two distinct crop scopes. Remaining disagreements stay flagged in "
                "`UNRESOLVED_CELLS.csv` for the later Codex source audit. The five pilot "
                "districts are intentionally excluded from these merged files.",
                "",
            ]
        )
        temporary = path.with_name(f".{path.name}.{time.time_ns()}.tmp")
        temporary.write_text("\n".join(lines), encoding="utf-8", newline="\n")
        temporary.replace(path)
        alias = self.final_root / "WORKFLOW_REPORT.md"
        alias.write_text("\n".join(lines), encoding="utf-8", newline="\n")
        return path

    def _load_or_create_state(self) -> dict[str, Any]:
        if self.state_path.is_file():
            state = json.loads(self.state_path.read_text(encoding="utf-8"))
            expected = {
                "config_sha256": self._config_sha,
                "metadata_sha256": self._metadata_sha,
                "selection_sha256": self._selection_sha,
            }
            changed = {
                key: (state.get(key), value)
                for key, value in expected.items()
                if state.get(key) != value
            }
            if changed:
                raise ValueError(f"Workflow inputs changed; use a new workflow id: {changed}")
            if state.get("selected_pdf_ids") != [item.pdf_id for item in self.documents]:
                raise ValueError("Workflow selected-PDF order changed")
            return state
        state = {
            "version": 3,
            "workflow_id": self.settings.workflow_id,
            "created_at": datetime.now(UTC).isoformat(),
            "stage": "NEW",
            "config": str(self.settings_path),
            "config_sha256": self._config_sha,
            "metadata_sha256": self._metadata_sha,
            "selection_sha256": self._selection_sha,
            "selected_pdf_ids": [item.pdf_id for item in self.documents],
            "excluded_districts": self.settings.excluded_districts,
        }
        self._save_state(state)
        return state

    def _save_state(self, state: dict[str, Any]) -> None:
        self.workflow_root.mkdir(parents=True, exist_ok=True)
        state["updated_at"] = datetime.now(UTC).isoformat()
        temporary = self.state_path.with_name(f".{self.state_path.name}.{time.time_ns()}.tmp")
        temporary.write_text(
            json.dumps(state, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        temporary.replace(self.state_path)

    @staticmethod
    def _atomic_json(path: Path, payload: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(f".{path.name}.{time.time_ns()}.tmp")
        temporary.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        temporary.replace(path)

    @staticmethod
    def _manifest_results(path: Path) -> dict[str, dict[str, Any]]:
        if not path.is_file():
            return {}
        payload = json.loads(path.read_text(encoding="utf-8"))
        return dict(payload.get("results", {}))

    def _guard_manifest_scope(self, results: dict[str, Any]) -> None:
        extra = sorted(set(results).difference(document.pdf_id for document in self.documents))
        if extra:
            raise ValueError(f"Workflow run manifest contains out-of-scope PDFs: {extra}")

    @staticmethod
    def _deduplicate_exclusions(
        exclusions: list[dict[str, str]],
    ) -> list[dict[str, str]]:
        selected: dict[str, dict[str, str]] = {}
        for item in exclusions:
            selected.setdefault(item["pdf_id"], item)
        return list(selected.values())

    def _blocked_result(
        self,
        state: dict[str, Any],
        status: str,
        failures: list[dict[str, str]],
        message: str,
    ) -> WorkflowResult:
        state["stage"] = status
        state["blocking_failures"] = failures
        self._save_state(state)
        return WorkflowResult(
            status,
            message,
            self.state_path,
        )
