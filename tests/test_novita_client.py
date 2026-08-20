from __future__ import annotations

import asyncio

import httpx
from PIL import Image

from census_extractor.config import PipelineConfig
from census_extractor.ocr.client import NovitaDeepSeekOCRClient, OCRRequestContext
from census_extractor.ocr.prompts import (
    FREE_OCR_PROMPT,
    GROUNDING_PROMPT,
    build_cell_free_ocr_prompt,
    build_page_grounding_prompt,
    build_row_grounding_prompt,
)
from census_extractor.pipeline.runner import PipelineRunner
from census_extractor.schemas import SchemaRegistry


def response_payload(content: str) -> dict:
    return {
        "choices": [{"message": {"content": content}}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 4, "total_tokens": 14},
    }


def test_novita_markup_parser_and_explicit_coordinate_system():
    payload = response_payload("<|ref|>Agra<|/ref|><|det|>[[100,200,400,350]]<|/det|>")
    result = NovitaDeepSeekOCRClient.parse_response(payload, 3, 1)
    assert result.has_usable_boxes
    assert result.tokens[0].text == "Agra"
    assert result.tokens[0].bbox == [100.0, 200.0, 400.0, 350.0]
    assert result.tokens[0].coordinate_system == "normalized_1000"
    assert result.usage.total_tokens == 14
    assert result.response_hash


def test_parser_rejects_unusable_boxes():
    result = NovitaDeepSeekOCRClient.parse_response(
        response_payload("<|ref|>bad<|/ref|><|det|>[[900,0,1100,50]]<|/det|>"), 0, 1
    )
    assert not result.has_usable_boxes
    assert result.parse_issues


def test_retry_after_then_success_and_cache(tmp_path):
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(429, headers={"Retry-After": "0"}, request=request)
        return httpx.Response(
            200,
            json=response_payload("<|ref|>1<|/ref|><|det|>[[10,10,90,90]]<|/det|>"),
            request=request,
        )

    config = PipelineConfig(
        output_dir=tmp_path,
        cache_path=tmp_path / "cache",
        novita_api_key="test-key-valid",
        retry_base_delay_sec=0,
        max_retries=2,
    )

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
            client = NovitaDeepSeekOCRClient(config, http)
            context = OCRRequestContext("a" * 64, (1, 2, 30, 40), 0, 1, "panel", GROUNDING_PROMPT)
            first = await client.ocr_crop_async(Image.new("RGB", (30, 20), "white"), context)
            second = await client.ocr_crop_async(Image.new("RGB", (30, 20), "white"), context)
            return client, first, second

    client, first, second = asyncio.run(run())
    assert calls == 2
    assert len(first.attempts) == 2
    assert second.cache_hit
    assert client.cache_hits == 1


def test_cache_key_invalidates_on_crop_or_prompt(tmp_path):
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(
            200,
            json=response_payload("<|ref|>x<|/ref|><|det|>[[10,10,90,90]]<|/det|>"),
            request=request,
        )

    config = PipelineConfig(
        output_dir=tmp_path, cache_path=tmp_path / "cache", novita_api_key="test-key-valid"
    )

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
            client = NovitaDeepSeekOCRClient(config, http)
            image = Image.new("RGB", (20, 20), "white")
            await client.ocr_crop_async(
                image, OCRRequestContext("b" * 64, (0, 0, 20, 20), 0, 1, "p")
            )
            await client.ocr_crop_async(
                image, OCRRequestContext("b" * 64, (1, 0, 21, 20), 0, 1, "p")
            )

    asyncio.run(run())
    assert calls == 2


def test_payload_is_single_turn_single_image(tmp_path):
    config = PipelineConfig(output_dir=tmp_path, novita_api_key="test-key-valid")
    client = NovitaDeepSeekOCRClient(config)
    payload = client._payload(
        client.image_to_png(Image.new("RGB", (5, 5), "white")), GROUNDING_PROMPT
    )
    assert payload["model"] == "deepseek/deepseek-ocr-2"
    assert len(payload["messages"]) == 1
    assert sum(item["type"] == "image_url" for item in payload["messages"][0]["content"]) == 1
    assert payload["temperature"] == payload["top_k"] == 0
    assert payload["max_tokens"] == 2048


def test_schema_prompts_explain_table_columns_without_authorizing_inference(
    project_config,
):
    schemas = SchemaRegistry(project_config.schemas_dir)
    civic = schemas.require("format_001")
    anchor = civic.row_anchor_panel
    row_prompt = build_row_grounding_prompt(civic, anchor)

    assert row_prompt.startswith(GROUNDING_PROMPT)
    assert "Civic and Other Amenities" in row_prompt
    assert "3: Road Length (km)" in row_prompt
    assert "field=road_length_km" in row_prompt
    assert "possible printed forms: PR 12.50 KR 3.20" in row_prompt
    assert "never answers" in row_prompt
    assert "Do not infer, calculate, normalize, correct" in row_prompt

    column = civic.get_column_by_var("road_length_km")
    assert column is not None
    cell_prompt = build_cell_free_ocr_prompt(civic, anchor, column)
    assert cell_prompt.startswith(FREE_OCR_PROMPT)
    assert "one cell" in cell_prompt
    assert "Return only the visible cell text" in cell_prompt

    tahsil = schemas.require("format_003")
    page_prompt = build_page_grounding_prompt(tahsil, 1)
    assert page_prompt.startswith(GROUNDING_PROMPT)
    assert "tahsil_education: printed column sequence 1, 2, 3" in page_prompt
    assert "tahsil_power_water: printed column sequence 1, 2, 25" in page_prompt


def test_ocr_row_uses_expected_column_context(project_config, tmp_path):
    captured_prompt = ""

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal captured_prompt
        captured_prompt = request.read().decode("utf-8")
        return httpx.Response(
            200,
            json=response_payload("<|ref|>1<|/ref|><|det|>[[10,10,90,90]]<|/det|>"),
            request=request,
        )

    schema = SchemaRegistry(project_config.schemas_dir).require("format_001")
    config = project_config.with_overrides(
        output_dir=tmp_path,
        cache_path=tmp_path / "cache",
        novita_api_key="test-key-valid",
    )

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
            client = NovitaDeepSeekOCRClient(config, http)
            await client.ocr_row_async(
                Image.new("RGB", (20, 20), "white"),
                0,
                1,
                schema.columns_for_panel(schema.row_anchor_panel),
            )

    asyncio.run(run())
    assert "Road Length (km)" in captured_prompt
    assert "Expected printed columns" in captured_prompt


def test_page_grounding_line_is_split_into_positioned_words():
    result = NovitaDeepSeekOCRClient.parse_response(
        response_payload("<|ref|>1 2 25 26<|/ref|><|det|>[[100,200,900,300]]<|/det|>"),
        -1,
        1,
    )
    words = PipelineRunner._grounded_tokens_to_words(result, 1000, 2000)
    assert [word["text"] for word in words] == ["1", "2", "25", "26"]
    centers = [(word["bbox"][0] + word["bbox"][2]) / 2 for word in words]
    assert centers == sorted(centers)
