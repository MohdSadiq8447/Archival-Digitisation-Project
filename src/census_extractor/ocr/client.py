"""Novita DeepSeek OCR 2 client with grounded parsing, retries, and caching."""

from __future__ import annotations

import asyncio
import base64
import hashlib
import io
import json
import random
import re
import time
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any

import httpx
from PIL import Image

from census_extractor.config import PipelineConfig, default_config
from census_extractor.ocr.prompts import (
    FREE_OCR_PROMPT,
    GROUNDING_PROMPT,
    build_columns_grounding_prompt,
)
from census_extractor.schemas import ColumnDefinition


class NovitaConfigurationError(RuntimeError):
    """Live OCR was requested without valid Novita credentials."""


@dataclass(slots=True)
class OCRToken:
    text: str
    bbox: list[float] | None = None
    coordinate_system: str = "normalized_1000"
    confidence: float | None = None


@dataclass(slots=True)
class AttemptMetadata:
    attempt: int
    status_code: int | None
    started_at: str
    duration_ms: int
    transient_error: str | None = None


@dataclass(slots=True)
class OCRUsage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


@dataclass(slots=True)
class OCRResult:
    row_index: int
    page_number: int
    raw_text: str
    tokens: list[OCRToken] = field(default_factory=list)
    raw_response: dict[str, Any] | None = None
    usage: OCRUsage = field(default_factory=OCRUsage)
    attempts: list[AttemptMetadata] = field(default_factory=list)
    response_hash: str | None = None
    cache_key: str | None = None
    cache_hit: bool = False
    prompt: str = GROUNDING_PROMPT
    prompt_version: str = ""
    model: str = ""
    parse_issues: list[str] = field(default_factory=list)
    error: str | None = None

    @property
    def has_usable_boxes(self) -> bool:
        return bool(self.tokens) and all(
            token.bbox is not None
            and len(token.bbox) == 4
            and 0 <= token.bbox[0] < token.bbox[2] <= 1000
            and 0 <= token.bbox[1] < token.bbox[3] <= 1000
            for token in self.tokens
        )


@dataclass(frozen=True, slots=True)
class OCRRequestContext:
    pdf_sha256: str
    crop_bbox: tuple[int, int, int, int]
    row_index: int
    page_number: int
    panel_id: str
    prompt: str = GROUNDING_PROMPT


class NovitaOCRCache:
    """Content-addressed successful responses and exact PNG crops."""

    def __init__(self, root: Path):
        self.root = Path(root)

    @staticmethod
    def make_key(
        context: OCRRequestContext,
        model: str,
        prompt_version: str,
        png_sha256: str,
    ) -> str:
        payload = {
            "pdf_sha256": context.pdf_sha256,
            "crop_bbox": context.crop_bbox,
            "page_number": context.page_number,
            "panel_id": context.panel_id,
            "model": model,
            "prompt": context.prompt,
            "prompt_version": prompt_version,
            "png_sha256": png_sha256,
        }
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(encoded).hexdigest()

    def load(self, key: str) -> dict[str, Any] | None:
        response_path = self.root / key[:2] / key / "response.json"
        if not response_path.is_file():
            return None
        try:
            value = json.loads(response_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        return value if value.get("ok") is True else None

    def store(self, key: str, png: bytes, response: dict[str, Any]) -> None:
        entry = self.root / key[:2] / key
        entry.mkdir(parents=True, exist_ok=True)
        self._atomic_bytes(entry / "crop.png", png)
        payload = {"ok": True, "cached_at": datetime.now(UTC).isoformat(), "response": response}
        self._atomic_bytes(
            entry / "response.json",
            json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8"),
        )

    @staticmethod
    def _atomic_bytes(path: Path, data: bytes) -> None:
        temporary = path.with_name(f".{path.name}.{time.time_ns()}.tmp")
        temporary.write_bytes(data)
        temporary.replace(path)


class NovitaDeepSeekOCRClient:
    """A single reusable HTTP client and semaphore for an entire pipeline run."""

    def __init__(
        self,
        config: PipelineConfig | None = None,
        http_client: httpx.AsyncClient | None = None,
    ):
        self.config = config or default_config
        self.api_key = self.config.novita_api_key
        self.base_url = self.config.novita_base_url
        self.model = self.config.novita_model
        cache_path = self.config.cache_path
        assert cache_path is not None
        self.cache = NovitaOCRCache(cache_path)
        self._semaphore = asyncio.Semaphore(self.config.global_concurrency)
        self._external_http_client = http_client is not None
        self._http_client = http_client
        self.cache_hits = 0
        self.cache_misses = 0

    def is_configured(self) -> bool:
        return self.config.is_novita_configured

    async def __aenter__(self) -> "NovitaDeepSeekOCRClient":
        await self._get_http_client()
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        if self._http_client is not None and not self._external_http_client:
            await self._http_client.aclose()
            self._http_client = None

    async def _get_http_client(self) -> httpx.AsyncClient:
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.config.request_timeout_sec)
            )
        return self._http_client

    @staticmethod
    def image_to_png(image: Image.Image) -> bytes:
        buffer = io.BytesIO()
        image.convert("RGB").save(buffer, format="PNG", optimize=False)
        return buffer.getvalue()

    async def ocr_crop_async(self, image: Image.Image, context: OCRRequestContext) -> OCRResult:
        if not self.is_configured():
            raise NovitaConfigurationError(
                "NOVITA_API_KEY is required for live extraction. Use --dry-run for geometry-only inspection."
            )
        png = self.image_to_png(image)
        png_sha = hashlib.sha256(png).hexdigest()
        key = self.cache.make_key(context, self.model, self.config.prompt_version, png_sha)
        cached = self.cache.load(key)
        if cached is not None:
            self.cache_hits += 1
            result = self.parse_response(cached["response"], context.row_index, context.page_number)
            result.cache_hit = True
            result.cache_key = key
            result.prompt = context.prompt
            result.prompt_version = self.config.prompt_version
            result.model = self.model
            return result
        self.cache_misses += 1

        payload = self._payload(png, context.prompt)
        attempts: list[AttemptMetadata] = []
        response_data: dict[str, Any] | None = None
        final_error: str | None = None
        async with self._semaphore:
            client = await self._get_http_client()
            for attempt in range(1, self.config.max_retries + 1):
                started = datetime.now(UTC)
                monotonic_start = time.monotonic()
                status_code: int | None = None
                transient: str | None = None
                response: httpx.Response | None = None
                try:
                    response = await client.post(
                        f"{self.base_url}/chat/completions",
                        headers={
                            "Authorization": f"Bearer {self.api_key}",
                            "Content-Type": "application/json",
                        },
                        json=payload,
                    )
                    status_code = response.status_code
                    if response.status_code == 200:
                        response_data = response.json()
                    elif response.status_code == 429 or response.status_code >= 500:
                        transient = f"HTTP {response.status_code}"
                    else:
                        final_error = (
                            f"Novita returned HTTP {response.status_code}: {response.text[:500]}"
                        )
                except (httpx.TimeoutException, httpx.NetworkError) as exc:
                    transient = f"{type(exc).__name__}: {exc}"
                duration_ms = round((time.monotonic() - monotonic_start) * 1000)
                attempts.append(
                    AttemptMetadata(
                        attempt=attempt,
                        status_code=status_code,
                        started_at=started.isoformat(),
                        duration_ms=duration_ms,
                        transient_error=transient,
                    )
                )
                if response_data is not None or final_error is not None:
                    break
                if attempt < self.config.max_retries:
                    retry_after = (
                        self._retry_after_seconds(response) if response is not None else None
                    )
                    await asyncio.sleep(
                        retry_after
                        if retry_after is not None
                        else self.config.retry_base_delay_sec * (2 ** (attempt - 1))
                        + random.uniform(0, 0.25)
                    )

        if response_data is None:
            return OCRResult(
                row_index=context.row_index,
                page_number=context.page_number,
                raw_text="",
                attempts=attempts,
                cache_key=key,
                prompt=context.prompt,
                prompt_version=self.config.prompt_version,
                model=self.model,
                error=final_error or "Novita request exhausted transient retries",
            )

        result = self.parse_response(response_data, context.row_index, context.page_number)
        result.attempts = attempts
        result.cache_key = key
        result.prompt = context.prompt
        result.prompt_version = self.config.prompt_version
        result.model = self.model
        if not result.raw_text.strip():
            result.error = "Novita returned empty OCR content"
            return result
        # Non-empty HTTP 200 responses are stable and cacheable even when their
        # OCR markup has parse issues; empty/transient failures are never cached.
        self.cache.store(key, png, response_data)
        return result

    async def ocr_row_async(
        self,
        image: Image.Image,
        row_index: int,
        page_number: int,
        expected_columns: list[ColumnDefinition] | None = None,
        *,
        pdf_sha256: str = "unknown",
        crop_bbox: tuple[int, int, int, int] | None = None,
        panel_id: str = "unknown",
        prompt: str = GROUNDING_PROMPT,
        **_: Any,
    ) -> OCRResult:
        if expected_columns and prompt == GROUNDING_PROMPT:
            prompt = build_columns_grounding_prompt(expected_columns)
        context = OCRRequestContext(
            pdf_sha256=pdf_sha256,
            crop_bbox=crop_bbox or (0, 0, image.width, image.height),
            row_index=row_index,
            page_number=page_number,
            panel_id=panel_id,
            prompt=prompt,
        )
        return await self.ocr_crop_async(image, context)

    async def ocr_cell_async(
        self,
        image: Image.Image,
        context: OCRRequestContext,
    ) -> OCRResult:
        padded = self._pad_and_upscale(image)
        free_context = OCRRequestContext(
            pdf_sha256=context.pdf_sha256,
            crop_bbox=context.crop_bbox,
            row_index=context.row_index,
            page_number=context.page_number,
            panel_id=context.panel_id,
            prompt=(
                context.prompt if context.prompt.startswith(FREE_OCR_PROMPT) else FREE_OCR_PROMPT
            ),
        )
        return await self.ocr_crop_async(padded, free_context)

    @staticmethod
    def _pad_and_upscale(image: Image.Image) -> Image.Image:
        from PIL import ImageOps

        padding = max(8, round(max(image.size) * 0.08))
        padded = ImageOps.expand(image.convert("RGB"), border=padding, fill="white")
        return padded.resize((padded.width * 2, padded.height * 2), Image.Resampling.LANCZOS)

    def _payload(self, png: bytes, prompt: str) -> dict[str, Any]:
        encoded = base64.b64encode(png).decode("ascii")
        preset = prompt
        schema_context = ""
        for candidate in (GROUNDING_PROMPT, FREE_OCR_PROMPT):
            if prompt.startswith(candidate):
                preset = candidate
                schema_context = prompt[len(candidate) :].strip()
                break
        messages: list[dict[str, Any]] = []
        if schema_context:
            messages.append({"role": "system", "content": schema_context})
        messages.append(
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{encoded}"},
                    },
                    {"type": "text", "text": preset},
                ],
            }
        )
        return {
            "model": self.model,
            "messages": messages,
            "temperature": 0,
            "top_k": 0,
            "max_tokens": self.config.max_tokens,
        }

    @classmethod
    def parse_response(
        cls, response: dict[str, Any], row_index: int, page_number: int
    ) -> OCRResult:
        issues: list[str] = []
        try:
            content = response["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            return OCRResult(
                row_index=row_index,
                page_number=page_number,
                raw_text="",
                raw_response=response,
                parse_issues=[f"Missing response content: {exc}"],
                error="Invalid Novita response envelope",
            )
        if not isinstance(content, str):
            content = str(content)
            issues.append("Message content was not a string")

        tokens: list[OCRToken] = []
        pattern = re.compile(
            r"<\|ref\|>(.*?)<\|/ref\|>\s*<\|det\|>(.*?)<\|/det\|>",
            re.DOTALL,
        )
        for match in pattern.finditer(content):
            text = match.group(1).strip()
            boxes = cls._parse_boxes(match.group(2))
            if not boxes:
                issues.append(f"Grounded ref {text!r} has no usable box")
                continue
            for box in boxes:
                tokens.append(OCRToken(text=text, bbox=box))
        if not tokens:
            shorthand_pattern = re.compile(
                r"(?:^|\s)([^\[\r\n]+?)\s*(\[\[\s*-?\d+(?:\.\d+)?\s*,\s*-?\d+(?:\.\d+)?\s*,\s*-?\d+(?:\.\d+)?\s*,\s*-?\d+(?:\.\d+)?\s*\]\])"
            )
            for match in shorthand_pattern.finditer(content):
                text = match.group(1).strip()
                boxes = cls._parse_boxes(match.group(2))
                for box in boxes:
                    tokens.append(OCRToken(text=text, bbox=box))
        if not tokens:
            issues.append("No grounded markup or shorthand tokens were parsed")

        usage_raw = response.get("usage") or {}
        usage = OCRUsage(
            prompt_tokens=int(usage_raw.get("prompt_tokens") or 0),
            completion_tokens=int(usage_raw.get("completion_tokens") or 0),
            total_tokens=int(usage_raw.get("total_tokens") or 0),
        )
        response_hash = hashlib.sha256(
            json.dumps(response, sort_keys=True, ensure_ascii=False).encode("utf-8")
        ).hexdigest()
        return OCRResult(
            row_index=row_index,
            page_number=page_number,
            raw_text=content,
            tokens=tokens,
            raw_response=response,
            usage=usage,
            response_hash=response_hash,
            parse_issues=issues,
        )

    @staticmethod
    def _parse_boxes(raw: str) -> list[list[float]]:
        parsed: object
        try:
            parsed = json.loads(raw.strip())
        except json.JSONDecodeError:
            parsed = [
                [float(value) for value in match]
                for match in re.findall(
                    r"\[\s*(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\s*\]",
                    raw,
                )
            ]
        if (
            isinstance(parsed, list)
            and len(parsed) == 4
            and all(isinstance(value, (int, float)) for value in parsed)
        ):
            parsed = [parsed]
        result: list[list[float]] = []
        if isinstance(parsed, list):
            for box in parsed:
                if (
                    isinstance(box, list)
                    and len(box) == 4
                    and all(isinstance(value, (int, float)) for value in box)
                ):
                    normalized: list[float] = []
                    for value in box:
                        if isinstance(value, (int, float)):
                            normalized.append(float(value))
                    if (
                        0 <= normalized[0] < normalized[2] <= 1000
                        and 0 <= normalized[1] < normalized[3] <= 1000
                    ):
                        result.append(normalized)
        return result

    @staticmethod
    def _retry_after_seconds(response: httpx.Response) -> float | None:
        value = response.headers.get("Retry-After")
        if not value:
            return None
        try:
            return max(0.0, float(value))
        except ValueError:
            try:
                retry_at = parsedate_to_datetime(value)
                if retry_at.tzinfo is None:
                    retry_at = retry_at.replace(tzinfo=UTC)
                return max(0.0, (retry_at - datetime.now(UTC)).total_seconds())
            except (TypeError, ValueError):
                return None

    @staticmethod
    def audit_record(result: OCRResult) -> dict[str, Any]:
        return {
            "row_index": result.row_index,
            "page_number": result.page_number,
            "raw_text": result.raw_text,
            "raw_response": result.raw_response,
            "grounded_tokens": [asdict(token) for token in result.tokens],
            "coordinate_system": "normalized_1000",
            "attempts": [asdict(attempt) for attempt in result.attempts],
            "usage": asdict(result.usage),
            "response_hash": result.response_hash,
            "cache_key": result.cache_key,
            "cache_hit": result.cache_hit,
            "prompt": result.prompt,
            "prompt_version": result.prompt_version,
            "model": result.model,
            "parse_issues": result.parse_issues,
            "error": result.error,
        }


# Transitional import compatibility; runtime behavior is Novita-only.
DeepSeekOCRClient = NovitaDeepSeekOCRClient
