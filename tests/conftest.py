from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from census_extractor.config import PipelineConfig  # noqa: E402


@pytest.fixture(scope="session")
def project_config() -> PipelineConfig:
    return PipelineConfig(base_dir=ROOT, render_dpi=300, auto_deskew=False)
