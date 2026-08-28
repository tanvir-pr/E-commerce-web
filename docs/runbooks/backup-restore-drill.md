# Postgres backup & restore drill (Solum)

Targets from the store spec: **RPO ≤ 15 minutes**, **RTO ≤ 2 hours**. Run this drill at least monthly and before each production launch.

## Daily backup (Compose / Hostinger)

```bash
# From repo root — dump while Postgres is healthy
docker compose exec -T postgres pg_dump -U store -d store -Fc > backups/store-$(date +%Y%m%d-%H%M).dump
```

Encrypt and ship the dump off-box (object storage or Hostinger backup). Keep at least 7 daily + 4 weekly copies.

## Restore drill (staging or throwaway volume)

1. Record the dump filename and checksum.
2. Stop API/worker writers:
   ```bash
   docker compose stop api worker web
   ```
3. Restore into a **new** database (never overwrite prod on the first try):
   ```bash
   docker compose exec -T postgres dropdb -U store store_restore --if-exists
   docker compose exec -T postgres createdb -U store store_restore
   cat backups/store-YYYYMMDD-HHMM.dump | docker compose exec -T postgres pg_restore -U store -d store_restore --clean --if-exists
   ```
4. Spot-check: `alembic_version`, recent `orders`, `stock_batches.qty_on_hand ≥ 0`, feature flags.
5. Time the restore end-to-end — must fit RTO.
6. Sign off below; attach the dump name and wall-clock minutes.

## Sign-off

| Field | Value |
| --- | --- |
| Date | |
| Operator | |
| Dump file | |
| Restore minutes | |
| Checks passed (Y/N) | |
| Notes | |

## Rollback pairing

Before a production deploy: take a dump, note the running image tag (`store-api:week1` digests), and keep the previous Alembic revision (`alembic history`). Launch readiness lists this under `rollback`.
