"""Filesystem layout under MEDIA_ROOT."""

from pathlib import Path
from uuid import UUID

from app.config import Settings


class MediaStorage:
    def __init__(self, settings: Settings) -> None:
        self.root = Path(settings.media_root)
        self.url_path = settings.media_url_path.rstrip("/")

    def product_image_dir(self, product_id: UUID, image_id: UUID) -> Path:
        path = self.root / "products" / str(product_id) / str(image_id)
        path.mkdir(parents=True, exist_ok=True)
        return path

    def relative_url(self, relative_path: str) -> str:
        return f"{self.url_path}/{relative_path.replace(chr(92), '/')}"

    def write_bytes(self, relative_path: str, data: bytes) -> None:
        full = self.root / relative_path
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_bytes(data)

    def delete_tree(self, product_id: UUID, image_id: UUID) -> None:
        path = self.root / "products" / str(product_id) / str(image_id)
        if not path.exists():
            return
        for child in path.rglob("*"):
            if child.is_file():
                child.unlink(missing_ok=True)
        for child in sorted(path.rglob("*"), reverse=True):
            if child.is_dir():
                child.rmdir()
        path.rmdir()
