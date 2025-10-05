"""Address book persistence."""

from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.address import Address
from app.problems import PROBLEM_NOT_FOUND, ProblemError


class AddressRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_for_user(self, user_id: UUID) -> list[Address]:
        result = await self.session.execute(
            select(Address)
            .where(Address.user_id == user_id)
            .order_by(Address.is_default.desc(), Address.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_owned(self, user_id: UUID, address_id: UUID) -> Address:
        result = await self.session.execute(
            select(Address).where(Address.id == address_id, Address.user_id == user_id)
        )
        row = result.scalar_one_or_none()
        if row is None:
            raise ProblemError(404, "Not found", "Address not found.", PROBLEM_NOT_FOUND)
        return row

    async def add(self, address: Address) -> Address:
        if address.is_default:
            await self._clear_default(address.user_id)
        self.session.add(address)
        await self.session.flush()
        return address

    async def save(self, address: Address) -> Address:
        if address.is_default:
            await self._clear_default(address.user_id, except_id=address.id)
        await self.session.flush()
        return address

    async def delete(self, address: Address) -> None:
        await self.session.delete(address)

    async def _clear_default(self, user_id: UUID, except_id: UUID | None = None) -> None:
        stmt = (
            update(Address)
            .where(Address.user_id == user_id, Address.is_default.is_(True))
            .values(is_default=False)
        )
        if except_id is not None:
            stmt = stmt.where(Address.id != except_id)
        await self.session.execute(stmt)
