"""Resize uploads, strip EXIF, emit WebP and AVIF derivatives."""

from __future__ import annotations

import io
from dataclasses import dataclass
from typing import Any

from PIL import Image, ImageOps

from app.problems import PROBLEM_VALIDATION, ProblemError

try:
    import pillow_avif  # type: ignore[import-untyped]  # noqa: F401
except ImportError:  # pragma: no cover - optional at runtime
    pillow_avif = None


@dataclass(frozen=True)
class DerivativeBytes:
    size_key: str
    width: int
    height: int
    webp: bytes
    avif: bytes | None


@dataclass(frozen=True)
class ProcessedImage:
    width: int
    height: int
    derivatives: list[DerivativeBytes]


def process_upload(
    raw: bytes,
    *,
    thumb_max: int,
    card_max: int,
    full_max: int,
) -> ProcessedImage:
    try:
        opened = Image.open(io.BytesIO(raw))
        opened.load()
    except Exception as exc:  # noqa: BLE001 — Pillow raises many types
        raise ProblemError(
            422,
            "Validation error",
            "Upload is not a readable image.",
            PROBLEM_VALIDATION,
        ) from exc

    # Apply EXIF orientation then drop all EXIF/metadata by rebuilding pixels.
    oriented = ImageOps.exif_transpose(opened)
    rgba = oriented.convert("RGBA")
    # Flatten onto white so WebP/AVIF stay opaque for product photos.
    background = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
    flat = Image.alpha_composite(background, rgba).convert("RGB")
    master_w, master_h = flat.size

    sizes = (
        ("thumb", thumb_max),
        ("card", card_max),
        ("full", full_max),
    )
    derivatives: list[DerivativeBytes] = []
    for size_key, max_edge in sizes:
        resized = _fit(flat, max_edge)
        webp = _encode(resized, "WEBP", quality=82)
        avif = _encode_avif(resized)
        derivatives.append(
            DerivativeBytes(
                size_key=size_key,
                width=resized.width,
                height=resized.height,
                webp=webp,
                avif=avif,
            )
        )
    return ProcessedImage(width=master_w, height=master_h, derivatives=derivatives)


def _fit(image: Image.Image, max_edge: int) -> Image.Image:
    width, height = image.size
    longest = max(width, height)
    if longest <= max_edge:
        return image.copy()
    scale = max_edge / float(longest)
    new_size = (max(1, int(width * scale)), max(1, int(height * scale)))
    return image.resize(new_size, Image.Resampling.LANCZOS)


def _encode(image: Image.Image, format_name: str, *, quality: int) -> bytes:
    buffer = io.BytesIO()
    # No exif= kwarg → metadata stripped.
    save_kwargs: dict[str, Any] = {"format": format_name, "quality": quality}
    if format_name == "WEBP":
        save_kwargs["method"] = 4
    image.save(buffer, **save_kwargs)
    return buffer.getvalue()


def _encode_avif(image: Image.Image) -> bytes | None:
    if pillow_avif is None:
        return None
    try:
        buffer = io.BytesIO()
        image.save(buffer, format="AVIF", quality=55)
        return buffer.getvalue()
    except Exception:  # noqa: BLE001
        return None
