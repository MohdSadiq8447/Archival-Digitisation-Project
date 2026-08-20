from __future__ import annotations

from pathlib import Path

import pytest

from census_extractor.metadata import MetadataError, MetadataRegistry
from census_extractor.schemas import PanelDefinition, SchemaRegistry


def test_workbook_loads_all_documents_and_preserves_multiword_district(project_config):
    registry = MetadataRegistry(project_config.metadata_path)
    assert len(registry.all()) == 157
    record = registry.get_for_pdf(project_config.pdfs_dir / "bara_banki_civic_1971.pdf")
    assert record.district == "Bara Banki"
    assert record.format_id == "format_001"
    assert len(record.workbook_sha256) == 64


def test_workbook_lookup_fails_closed(project_config):
    registry = MetadataRegistry(project_config.metadata_path)
    with pytest.raises(MetadataError, match="No authoritative metadata"):
        registry.get_for_pdf(Path("invented_civic_1971.pdf"))


def test_physical_panel_schemas(project_config):
    schemas = SchemaRegistry(project_config.schemas_dir)
    civic = schemas.require("format_001")
    mededu = schemas.require("format_002")
    tahsil = schemas.require("format_003")
    assert [panel.printed_columns for panel in civic.panels] == [
        list(range(1, 9)),
        list(range(9, 17)),
    ]
    assert [panel.printed_columns for panel in mededu.panels] == [
        list(range(1, 10)),
        list(range(10, 18)),
    ]
    assert len(tahsil.panels) == 4
    assert tahsil.panels[1].printed_columns == [1, 2, *range(25, 39)]
    assert tahsil.row_anchor_panel.panel_id == "tahsil_education"
    assert tahsil.total_columns == 50


def test_unknown_schema_and_invalid_panel_fail_closed(project_config):
    schemas = SchemaRegistry(project_config.schemas_dir)
    with pytest.raises(ValueError, match="Unknown format"):
        schemas.require("format_999")
    with pytest.raises(ValueError, match="unique"):
        PanelDefinition(panel_id="bad", page=1, printed_columns=[1, 1])
