# ADR 0004: Meilisearch for catalog search

## Status

Accepted (Part 10)

## Context

The storefront needs full-text search over products with faceted filters for skin type, concern, and ingredient. Postgres `ILIKE` is enough for tiny catalogs but not for facet aggregation or typo-tolerant ranking.

## Decision

Use **Meilisearch** as the search index. Postgres remains the source of truth for catalog data. Published, non-deleted products are upserted into a `products` index; drafts, archives, and soft-deletes are removed. Public `GET /api/v1/search` queries Meilisearch. Staff can rebuild with `POST /api/v1/admin/search/reindex`.

## Consequences

- Compose runs a `meilisearch` service; API/worker wait on its health check.
- Catalog writes sync the index best-effort (failures are logged, not raised) so admin CRUD stays available if search is down.
- Part 12 storefront search UI will call the same API.
