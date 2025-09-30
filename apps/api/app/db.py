"""SQLAlchemy declarative base. Import models so metadata is populated."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


# noqa: F401 — register metadata for Alembic
from app import models as _models  # noqa: E402, F401
