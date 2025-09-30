"""Test env defaults so Settings can load without Docker."""

import os

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://store:store@localhost:5432/store")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("JWT_SECRET", "test-secret")
os.environ.setdefault("BREACH_CHECK", "stub")
