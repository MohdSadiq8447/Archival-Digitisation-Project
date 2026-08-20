"""Runtime configuration for the census extraction pipeline."""

from __future__ import annotations

import os
from dataclasses import dataclass, field, replace
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


def _default_base_dir() -> Path:
    configured = os.getenv("CENSUS_PROJECT_ROOT")
    candidates = [Path(configured)] if configured else []
    candidates.extend([Path.cwd(), Path(__file__).resolve().parents[2]])
    for candidate in candidates:
        if (candidate / "1971_Trimmed_PDF" / "Uttar_Pradesh").is_dir():
            return candidate
    return Path(__file__).resolve().parents[2]


@dataclass(slots=True)
class PipelineConfig:
    """Configuration without filesystem side effects."""

    base_dir: Path = field(default_factory=_default_base_dir)
    output_dir: Path | None = None
    cache_path: Path | None = None
    render_dpi: int = 300
    auto_deskew: bool = True
    crop_padding_px: int = 8
    novita_api_key: str = field(default_factory=lambda: os.getenv("NOVITA_API_KEY", "").strip())
    novita_base_url: str = field(
        default_factory=lambda: os.getenv(
            "NOVITA_BASE_URL", "https://api.novita.ai/openai/v1"
        ).rstrip("/")
    )
    novita_model: str = field(
        default_factory=lambda: os.getenv("NOVITA_MODEL", "deepseek/deepseek-ocr-2")
    )
    global_concurrency: int = 2
    request_timeout_sec: float = 90.0
    max_retries: int = 4
    retry_base_delay_sec: float = 1.0
    max_tokens: int = 2048
    quality_threshold: float = 0.95
    prompt_version: str = "novita-deepseek-ocr2-schema-system-context-v4"
    data_dir: Path = field(init=False)
    metadata_path: Path = field(init=False)
    schemas_dir: Path = field(init=False)
    pdfs_dir: Path = field(init=False)
    outputs_dir: Path = field(init=False)
    runs_dir: Path = field(init=False)

    def __post_init__(self) -> None:
        self.base_dir = Path(self.base_dir).resolve()
        self.data_dir = self.base_dir / "1971_Trimmed_PDF" / "Uttar_Pradesh"
        self.metadata_path = self.data_dir / "metadata" / "document.xlsx"
        self.schemas_dir = self.data_dir / "schemas"
        self.pdfs_dir = self.data_dir / "pdfs"
        self.outputs_dir = (
            Path(self.output_dir).resolve()
            if self.output_dir is not None
            else self.data_dir / "outputs"
        )
        self.runs_dir = self.outputs_dir / "runs"
        self.cache_path = (
            Path(self.cache_path).resolve()
            if self.cache_path is not None
            else self.outputs_dir / "cache" / "novita"
        )
        if self.global_concurrency < 1:
            raise ValueError("global_concurrency must be at least 1")
        if not 0 <= self.quality_threshold <= 1:
            raise ValueError("quality_threshold must be between 0 and 1")

    @property
    def is_novita_configured(self) -> bool:
        return len(self.novita_api_key) > 5

    def with_overrides(self, **changes: object) -> "PipelineConfig":
        return replace(self, **changes)


default_config = PipelineConfig()
