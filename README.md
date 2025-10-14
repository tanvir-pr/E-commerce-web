# Store

Parts 1–7 of a single-vendor skincare ecommerce site. Auth/account, catalog, products/variants, and product image upload (resize, WebP/AVIF, EXIF stripped; slots: product / texture / lifestyle). Staff and the seeded owner must enroll TOTP before an admin session is issued.

The browser talks to Next.js (host port **3001** → container 3000). Next.js proxies `/api/v1` to FastAPI. Use **http://localhost:3001**, not `127.0.0.1`. Postgres is on host port **5433**.

`DELETE /api/v1/users/me` sets `deleted_at` and revokes refresh sessions. It does not erase the row, free that email for reuse, or remove audit history. Full erasure is incomplete.

## Run

```powershell
cd D:\Full-web-4-project
Copy-Item .env.example .env
docker compose up --build -d
docker compose exec api python -m alembic upgrade head
docker compose exec api python -m app.scripts.seed_superadmin
docker compose exec api python -m app.scripts.seed_catalog
docker compose exec api python -m app.scripts.seed_products
```

Open http://localhost:3001/en

- Register: http://localhost:3001/en/register
- Mailpit: http://localhost:8025
- Sign in: http://localhost:3001/en/login
- Account: http://localhost:3001/en/account
- Forgot password: http://localhost:3001/en/forgot-password
- Catalog: `GET /api/v1/catalog/categories`, `GET /api/v1/catalog/attributes?kind=skin_type`
- Products: `GET /api/v1/catalog/products`, `GET /api/v1/catalog/products/{slug}`
- Images (staff): `POST /api/v1/admin/catalog/products/{id}/images` (multipart: file, slot, alt_text)
- Media files: `/api/v1/media/products/...`
- Seeded owner: `owner@example.com` / `ChangeMeNow1` → then `/en/enroll` (authenticator) → `/en/admin`
- API docs: http://localhost:8000/docs

Do not commit `.env`.

## Tests

```powershell
cd D:\Full-web-4-project\apps\api
python -m pip install -r requirements.txt -r requirements-dev.txt
python -m pytest
python -m ruff check app tests
python -m mypy app
```
