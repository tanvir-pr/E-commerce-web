"""MediaService upload using temp storage and fakes."""

import io
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from app.config import Settings
from app.media.service import MediaService
from app.problems import ProblemError
from PIL import Image


class FakeSession:
    def __init__(self) -> None:
        self.added: list[object] = []

    def add(self, obj: object) -> None:
        self.added.append(obj)

    async def flush(self) -> None:
        return None

    async def get(self, model: object, identity: UUID) -> object | None:
        _ = model
        for item in self.added:
            if getattr(item, "id", None) == identity:
                return item
        return None

    async def delete(self, obj: object) -> None:
        self.added = [item for item in self.added if item is not obj]


class FakeAudit:
    def __init__(self) -> None:
        self.actions: list[str] = []

    async def record(self, **kwargs: object) -> None:
        self.actions.append(str(kwargs.get("action")))


class FakeProducts:
    def __init__(self, product_id: UUID) -> None:
        self.product_id = product_id

    async def require(self, product_id: UUID) -> SimpleNamespace:
        if product_id != self.product_id:
            raise ProblemError(404, "Not found", "Product not found.", "x")
        return SimpleNamespace(id=product_id)


def _png() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (640, 480), color=(200, 40, 40)).save(buffer, format="PNG")
    return buffer.getvalue()


def _settings(tmp_path: object) -> Settings:
    return Settings(
        database_url="postgresql+asyncpg://store:store@localhost:5432/store",
        redis_url="redis://localhost:6379/0",
        media_root=str(tmp_path),
        media_url_path="/api/v1/media",
        media_thumb_max=160,
        media_card_max=320,
        media_full_max=640,
    )


@pytest.mark.asyncio
async def test_upload_writes_webp_derivatives(tmp_path: object) -> None:
    product_id = uuid4()
    session = FakeSession()
    service = MediaService(session, settings=_settings(tmp_path))  # type: ignore[arg-type]
    service.products = FakeProducts(product_id)  # type: ignore[assignment]
    service.audit = FakeAudit()  # type: ignore[assignment]

    out = await service.upload(
        product_id=product_id,
        slot="texture",
        filename="swatch.png",
        content_type="image/png",
        data=_png(),
        alt_text="Texture macro",
        actor_user_id=uuid4(),
    )
    assert out.slot == "texture"
    assert out.alt_text == "Texture macro"
    assert len(out.derivatives) == 3
    assert out.derivatives[0].webp_url.endswith(".webp")
    webp_path = tmp_path / "products" / str(product_id) / str(out.id) / "thumb.webp"  # type: ignore[operator]
    assert webp_path.exists()


@pytest.mark.asyncio
async def test_upload_rejects_bad_slot(tmp_path: object) -> None:
    product_id = uuid4()
    service = MediaService(FakeSession(), settings=_settings(tmp_path))  # type: ignore[arg-type]
    service.products = FakeProducts(product_id)  # type: ignore[assignment]
    service.audit = FakeAudit()  # type: ignore[assignment]
    with pytest.raises(ProblemError) as exc:
        await service.upload(
            product_id=product_id,
            slot="hero",
            filename="x.png",
            content_type="image/png",
            data=_png(),
            alt_text=None,
            actor_user_id=uuid4(),
        )
    assert exc.value.status == 422
