# Store

Part 2 of a single-vendor skincare ecommerce site. You can register, verify email in Mailpit, sign in with rotating refresh cookies, and sign out. Catalog and checkout are not built yet.

The browser talks to Next.js (host port **3001** → container 3000). Next.js proxies `/api/v1` to FastAPI. Use **http://localhost:3001**, not `127.0.0.1`, so `__Host-` cookies work. Postgres is on host port **5433**.

## Run

```powershell
cd D:\Full-web-4-project
Copy-Item .env.example .env
docker compose up --build -d
docker compose exec api python -m alembic upgrade head
docker compose exec api python -m app.scripts.seed_superadmin
```

Open http://localhost:3001/en — health should be ok.

- Register: http://localhost:3001/en/register
- Mailpit: http://localhost:8025
- Sign in: http://localhost:3001/en/login
- Seeded owner: `owner@example.com` / `ChangeMeNow1` (from `.env`)
- API docs: http://localhost:8000/docs

Do not commit `.env`.

Stop with `docker compose down`. `docker compose down -v` deletes the local database volume.

## Tests

```powershell
cd D:\Full-web-4-project\apps\api
python -m pip install -r requirements.txt -r requirements-dev.txt
python -m pytest
python -m ruff check app tests
python -m mypy app
```
