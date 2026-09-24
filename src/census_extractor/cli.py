"""Command-line interface for run-scoped census extraction."""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

from census_extractor.config import PipelineConfig
from census_extractor.pipeline.runner import ExtractionSummary, PipelineRunner
from census_extractor.postprocessing import CSVPostprocessor
from census_extractor.schemas import SchemaRegistry
from census_extractor.source_audit import SourceAuditRunner
from census_extractor.workflow import RemainingUPWorkflow


def _configure_console_output() -> None:
    """Keep Windows consoles from crashing on OCR symbols outside the code page."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(errors="backslashreplace")


def _common_run_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--output-dir", type=Path, help="Output root (runs and cache are created below it)"
    )
    identity = parser.add_mutually_exclusive_group()
    identity.add_argument("--run-id", help="Explicit run identifier")
    identity.add_argument("--resume", metavar="RUN_ID", help="Resume an existing run identifier")
    parser.add_argument(
        "--concurrency",
        type=int,
        default=2,
        help="Global Novita in-flight request limit (default: 2)",
    )
    parser.add_argument(
        "--retries", type=int, default=4, help="Maximum attempts for transient Novita failures"
    )
    parser.add_argument("--no-viz", action="store_true", help="Do not save geometry overlays")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Inspect metadata and geometry only; never call OCR or write clean data",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Historical Indian Census table extraction")
    commands = parser.add_subparsers(dest="command", required=True)
    process = commands.add_parser("process", help="Process one workbook-registered two-page PDF")
    process.add_argument("--pdf", required=True, type=Path)
    process.add_argument("--format", help="Guarded format override; must match workbook metadata")
    _common_run_options(process)

    batch = commands.add_parser("batch", help="Process a resumable PDF batch")
    batch.add_argument("--dir", type=Path)
    batch.add_argument("--pattern", default="*.pdf")
    batch.add_argument("--limit", type=int)
    batch.add_argument(
        "--pdf-workers",
        type=int,
        default=2,
        help="PDFs prepared concurrently; API requests still obey global concurrency",
    )
    _common_run_options(batch)

    geometry = commands.add_parser(
        "geometry", aliases=["test-geometry"], help="Geometry-only inspection for one PDF"
    )
    geometry.add_argument("--pdf", required=True, type=Path)
    geometry.add_argument("--output-dir", type=Path)
    geometry.add_argument("--run-id")
    geometry.add_argument("--no-viz", action="store_true")

    postprocess = commands.add_parser(
        "postprocess", help="Apply a source-verified correction ledger to one completed run"
    )
    postprocess.add_argument(
        "--source-run",
        required=True,
        help="Source run id below outputs/runs, or an absolute run directory",
    )
    postprocess.add_argument("--ledger", required=True, type=Path)
    postprocess.add_argument("--output-id", required=True)
    postprocess.add_argument(
        "--output-dir", type=Path, help="Output root containing runs and postprocessed"
    )

    source_audit = commands.add_parser(
        "source-audit", help="Validate Codex source decisions and build a v3 ledger"
    )
    source_audit.add_argument(
        "--provisional",
        required=True,
        type=Path,
        help="Provisional postprocessed folder or its absolute path",
    )
    source_audit.add_argument(
        "--decisions",
        type=Path,
        help="Completed JSONL decisions; omit when creating an audit queue",
    )
    source_audit.add_argument(
        "--queue",
        type=Path,
        help="Write a deterministic JSONL audit queue to this path",
    )
    source_audit.add_argument("--ledger", type=Path, help="Destination version-3 ledger path")
    source_audit.add_argument(
        "--output-dir", type=Path, help="Output root containing postprocessed folders"
    )

    workflow = commands.add_parser(
        "workflow", help="Run or resume the sequential remaining-UP workflow"
    )
    workflow.add_argument("--config", required=True, type=Path)
    workflow.add_argument(
        "--output-dir", type=Path, help="Output root containing runs and workflow state"
    )

    commands.add_parser("schemas", help="List registered logical schemas and physical panels")
    return parser


def _config(args: argparse.Namespace) -> PipelineConfig:
    return PipelineConfig(
        output_dir=getattr(args, "output_dir", None),
        global_concurrency=getattr(args, "concurrency", 2),
        max_retries=getattr(args, "retries", 4),
    )


def _resolve(path: Path, base: Path) -> Path:
    return path.resolve() if path.is_absolute() else (base / path).resolve()


def _print_summary(summary: ExtractionSummary) -> None:
    print(f"{summary.status}: {summary.pdf_name}")
    print(f"  run={summary.run_id} district={summary.district} format={summary.format_id}")
    print(
        f"  parent_rows={summary.parent_rows} rows={summary.total_rows} "
        f"valid={summary.valid_rows} quality={summary.quality_score:.2%}"
    )
    if summary.cache_metrics:
        print(
            f"  cache hits={summary.cache_metrics.get('hits', 0)} misses={summary.cache_metrics.get('misses', 0)}"
        )
    for failure in summary.actionable_failures[:10]:
        print(f"  failure: {failure}")
    for label, path in summary.exported_files.items():
        print(f"  {label}: {path}")


def _exit_code(summaries: list[ExtractionSummary]) -> int:
    if any(summary.status == "ERROR" for summary in summaries):
        return 1
    if any(summary.status == "QUARANTINED" for summary in summaries):
        return 2
    return 0


def main(argv: list[str] | None = None) -> int:
    _configure_console_output()
    args = build_parser().parse_args(argv)
    config = _config(args)
    if args.command == "schemas":
        for schema in SchemaRegistry(config.schemas_dir).all_formats():
            print(f"{schema.format_id}: {schema.name} ({schema.total_columns} logical columns)")
            for panel in schema.panels:
                print(f"  {panel.panel_id}: page {panel.page}, printed {panel.printed_columns}")
        return 0

    if args.command == "postprocess":
        try:
            result = CSVPostprocessor(config).run(
                source_run=args.source_run,
                ledger_path=_resolve(args.ledger, config.base_dir),
                output_id=args.output_id,
            )
        except Exception as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1
        print(f"SUCCESS: {len(result.csv_files)} corrected CSVs")
        print(f"  output={result.output_root}")
        print(f"  reviewed_unique_cells={result.reviewed_unique_cells}")
        print(f"  corrected_cells={result.corrected_cells}")
        print(f"  correction_log={result.correction_log}")
        print(f"  report={result.report}")
        return 0

    if args.command == "source-audit":
        try:
            provisional = args.provisional.resolve()
            if not provisional.is_dir():
                provisional = (config.outputs_dir / "postprocessed" / args.provisional).resolve()
            runner = SourceAuditRunner(provisional, config.schemas_dir)
            if bool(args.queue) == bool(args.decisions):
                raise ValueError("provide exactly one of --queue or --decisions")
            if args.queue:
                print(f"QUEUE: {runner.write_queue(_resolve(args.queue, config.base_dir))}")
            else:
                if not args.ledger:
                    raise ValueError("--ledger is required with --decisions")
                ledger = runner.build_ledger(
                    _resolve(args.decisions, config.base_dir),
                    _resolve(args.ledger, config.base_dir),
                )
                print(
                    f"LEDGER: {args.ledger} cells={ledger.expected_unique_source_cells} "
                    f"allow_unresolved={ledger.allow_unresolved}"
                )
        except Exception as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1
        return 0

    if args.command == "workflow":
        try:
            workflow = RemainingUPWorkflow(
                config,
                _resolve(args.config, config.base_dir),
            )
            result = workflow.run()
        except Exception as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1
        print(f"{result.status}: {result.message}")
        print(f"  state={result.state_path}")
        if result.review_workbook:
            print(f"  review={result.review_workbook}")
        if result.final_output:
            print(f"  output={result.final_output}")
        return 1 if result.status.startswith("BLOCKED_") else 0

    dry_run = args.command in {"geometry", "test-geometry"} or getattr(args, "dry_run", False)
    if not dry_run and not config.is_novita_configured:
        print(
            "ERROR: NOVITA_API_KEY is required for live process/batch. Use --dry-run for geometry-only inspection.",
            file=sys.stderr,
        )
        return 1
    run_id = getattr(args, "resume", None) or getattr(args, "run_id", None)
    try:
        runner = PipelineRunner(config, run_id=run_id, resume=bool(getattr(args, "resume", None)))
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    if args.command == "process":
        path = _resolve(args.pdf, config.base_dir)
        summary = runner.process_pdf(
            path, format_id=args.format, save_viz=not args.no_viz, is_dry_run=args.dry_run
        )
        _print_summary(summary)
        return _exit_code([summary])

    if args.command in {"geometry", "test-geometry"}:
        path = _resolve(args.pdf, config.base_dir)
        summary = runner.process_pdf(path, save_viz=not args.no_viz, is_dry_run=True)
        _print_summary(summary)
        return _exit_code([summary])

    pdf_dir = _resolve(args.dir, config.base_dir) if args.dir else config.pdfs_dir
    pdfs = sorted(pdf_dir.glob(args.pattern))
    if args.limit is not None:
        pdfs = pdfs[: args.limit]
    print(f"Processing {len(pdfs)} PDFs in run {runner.run_id}")
    summaries = asyncio.run(
        runner.process_batch_async(
            pdfs, save_viz=not args.no_viz, is_dry_run=args.dry_run, concurrency=args.pdf_workers
        )
    )
    for summary in summaries:
        _print_summary(summary)
    counts = {
        status: sum(summary.status == status for summary in summaries)
        for status in ("SUCCESS", "QUARANTINED", "ERROR", "DRY_RUN")
    }
    print("Completed: " + " ".join(f"{key}={value}" for key, value in counts.items()))
    return _exit_code(summaries)


if __name__ == "__main__":
    raise SystemExit(main())
