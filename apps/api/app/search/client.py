"""Thin async Meilisearch HTTP client."""

from __future__ import annotations

import asyncio
from typing import Any

import httpx
import structlog

from app.config import Settings, get_settings

log = structlog.get_logger()


class MeilisearchError(Exception):
    def __init__(self, message: str, *, status: int | None = None) -> None:
        super().__init__(message)
        self.status = status


class MeilisearchClient:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.base = self.settings.meilisearch_url.rstrip("/")
        self.index = self.settings.meilisearch_index
        self.api_key = self.settings.meilisearch_api_key

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    async def health(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                response = await client.get(f"{self.base}/health")
            return response.status_code == 200 and response.json().get("status") == "available"
        except Exception:
            return False

    async def ensure_index(self) -> None:
        async with httpx.AsyncClient(timeout=10.0) as client:
            existing = await client.get(
                f"{self.base}/indexes/{self.index}",
                headers=self._headers(),
            )
            if existing.status_code == 200:
                return
            response = await client.post(
                f"{self.base}/indexes",
                headers=self._headers(),
                json={"uid": self.index, "primaryKey": "id"},
            )
        if response.status_code == 409:
            return
        if response.status_code in {201, 202}:
            try:
                await self._wait_task(response.json())
            except MeilisearchError as exc:
                if "index_already_exists" in str(exc):
                    return
                raise
            return
        raise MeilisearchError(
            f"create index failed: {response.text}", status=response.status_code
        )

    async def configure_index(self) -> None:
        settings_body = {
            "searchableAttributes": [
                "name",
                "subtitle",
                "description",
                "ingredients_text",
                "ingredients",
                "concerns",
                "skin_types",
                "category_name",
                "slug",
            ],
            "filterableAttributes": [
                "category_slug",
                "skin_types",
                "concerns",
                "ingredients",
                "textures",
                "claims",
                "routine_step",
                "from_price_poisha",
                "status",
            ],
            "sortableAttributes": ["name", "from_price_poisha", "published_at"],
            "displayedAttributes": [
                "id",
                "slug",
                "name",
                "subtitle",
                "category_slug",
                "category_name",
                "routine_step",
                "from_price_poisha",
                "skin_types",
                "concerns",
                "ingredients",
                "textures",
                "claims",
                "published_at",
            ],
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.patch(
                f"{self.base}/indexes/{self.index}/settings",
                headers=self._headers(),
                json=settings_body,
            )
        if response.status_code not in {200, 202}:
            raise MeilisearchError(
                f"configure index failed: {response.text}", status=response.status_code
            )
        await self._wait_task(response.json())

    async def upsert_documents(self, documents: list[dict[str, Any]]) -> None:
        if not documents:
            return
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.base}/indexes/{self.index}/documents",
                headers=self._headers(),
                json=documents,
            )
        if response.status_code not in {200, 202}:
            raise MeilisearchError(
                f"upsert documents failed: {response.text}", status=response.status_code
            )
        await self._wait_task(response.json())

    async def delete_document(self, document_id: str) -> None:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.delete(
                f"{self.base}/indexes/{self.index}/documents/{document_id}",
                headers=self._headers(),
            )
        if response.status_code in {200, 202}:
            await self._wait_task(response.json())
            return
        if response.status_code == 404:
            return
        raise MeilisearchError(
            f"delete document failed: {response.text}", status=response.status_code
        )

    async def delete_all_documents(self) -> None:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.delete(
                f"{self.base}/indexes/{self.index}/documents",
                headers=self._headers(),
            )
        if response.status_code not in {200, 202}:
            raise MeilisearchError(
                f"delete all failed: {response.text}", status=response.status_code
            )
        await self._wait_task(response.json())

    async def search(self, body: dict[str, Any]) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{self.base}/indexes/{self.index}/search",
                headers=self._headers(),
                json=body,
            )
        if response.status_code != 200:
            raise MeilisearchError(
                f"search failed: {response.text}", status=response.status_code
            )
        payload = response.json()
        if not isinstance(payload, dict):
            raise MeilisearchError("search returned non-object JSON")
        return payload

    async def _wait_task(self, task_payload: dict[str, Any]) -> None:
        task_uid = task_payload.get("taskUid") or task_payload.get("uid")
        if task_uid is None:
            return
        # Upserts can sit behind settings tasks after boot; allow ~30s.
        async with httpx.AsyncClient(timeout=30.0) as client:
            for _ in range(150):
                response = await client.get(
                    f"{self.base}/tasks/{task_uid}",
                    headers=self._headers(),
                )
                if response.status_code != 200:
                    raise MeilisearchError(
                        f"task poll failed: {response.text}", status=response.status_code
                    )
                data = response.json()
                status = data.get("status")
                if status == "succeeded":
                    return
                if status == "failed":
                    raise MeilisearchError(f"meilisearch task failed: {data.get('error')}")
                if status == "canceled":
                    raise MeilisearchError(f"meilisearch task {task_uid} was canceled")
                await asyncio.sleep(0.2)
        raise MeilisearchError(f"meilisearch task {task_uid} timed out")
