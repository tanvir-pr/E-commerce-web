"""Image processing: EXIF strip, resize, WebP (and AVIF when available)."""

import io
from pathlib import Path

from app.media.processing import process_upload
from PIL import Image


def _png_bytes(*, size: tuple[int, int] = (1200, 800), with_exif: bool = False) -> bytes:
    image = Image.new("RGB", size, color=(32, 160, 96))
    buffer = io.BytesIO()
    if with_exif:
        # Pillow may ignore unknown EXIF; still round-trip through save/load.
        exif = image.getexif()
        exif[271] = "StoreTest"  # Make
        image.save(buffer, format="JPEG", quality=90, exif=exif)
    else:
        image.save(buffer, format="PNG")
    return buffer.getvalue()


def test_process_upload_builds_three_sizes_and_webp(tmp_path: Path) -> None:
    _ = tmp_path
    processed = process_upload(
        _png_bytes(),
        thumb_max=320,
        card_max=800,
        full_max=1600,
    )
    assert processed.width == 1200
    assert processed.height == 800
    assert [d.size_key for d in processed.derivatives] == ["thumb", "card", "full"]
    thumb = processed.derivatives[0]
    assert max(thumb.width, thumb.height) <= 320
    assert thumb.webp.startswith(b"RIFF")
    # AVIF is optional depending on pillow-avif-plugin wheels.
    if thumb.avif is not None:
        assert len(thumb.avif) > 32


def test_process_upload_strips_exif_by_reencode() -> None:
    raw = _png_bytes(with_exif=True)
    processed = process_upload(raw, thumb_max=200, card_max=400, full_max=800)
    webp = processed.derivatives[-1].webp
    reloaded = Image.open(io.BytesIO(webp))
    assert not reloaded.getexif()
