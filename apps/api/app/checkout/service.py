"""Checkout quote: reprice cart, stock check, shipping, verified contact."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.cart.schemas import CartOut
from app.cart.service import CartService
from app.checkout.schemas import (
    CheckoutAddressSnapshotOut,
    CheckoutContactOut,
    CheckoutQuoteIn,
    CheckoutQuoteOut,
    CheckoutStockLineOut,
)
from app.problems import (
    PROBLEM_CONTACT_UNVERIFIED,
    PROBLEM_UNAUTHORIZED,
    PROBLEM_VALIDATION,
    ProblemError,
)
from app.shipping.schemas import ShippingQuoteIn, ShippingQuoteLineIn
from app.shipping.service import ShippingService
from app.users.addresses import AddressRepository
from app.users.repository import UserRepository


class CheckoutService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.carts = CartService(session)
        self.shipping = ShippingService(session)
        self.users = UserRepository(session)
        self.addresses = AddressRepository(session)

    async def quote(
        self,
        body: CheckoutQuoteIn,
        *,
        user_id: UUID,
        guest_token: str | None,
    ) -> CheckoutQuoteOut:
        user = await self.users.get_by_id(user_id)
        if user is None or user.deleted_at is not None:
            raise ProblemError(401, "Unauthorized", "Sign in again.", PROBLEM_UNAUTHORIZED)

        email_ok = user.email_verified_at is not None
        phone_ok = user.phone_verified_at is not None
        contact = CheckoutContactOut(
            email_verified=email_ok,
            phone_verified=phone_ok,
            ok=email_ok or phone_ok,
        )
        if not contact.ok:
            raise ProblemError(
                403,
                "Contact unverified",
                "Verify your email or phone before checkout.",
                PROBLEM_CONTACT_UNVERIFIED,
            )

        address = await self._resolve_address(user_id, body)
        cart, _ = await self.carts.get_cart(user_id=user_id, guest_token=guest_token)
        if not cart.items:
            raise ProblemError(
                422,
                "Validation error",
                "Your bag is empty.",
                PROBLEM_VALIDATION,
            )

        stock = self._stock_lines(cart)
        stock_ok = all(line.ok for line in stock)

        shipping = await self.shipping.quote(
            ShippingQuoteIn(
                district=address.district,
                city=address.city,
                subtotal_poisha=cart.subtotal_poisha,
                lines=[
                    ShippingQuoteLineIn(variant_id=item.variant_id, qty=item.qty)
                    for item in cart.items
                ],
            )
        )

        blockers: list[str] = []
        if not stock_ok:
            blockers.append("stock")
        if shipping.charge_poisha < 0:
            blockers.append("shipping")

        merchandise = cart.subtotal_poisha
        ship_poisha = shipping.charge_poisha
        ready = contact.ok and stock_ok and bool(cart.items)

        return CheckoutQuoteOut(
            cart=cart,
            address=address,
            shipping=shipping,
            stock=stock,
            contact=contact,
            merchandise_subtotal_poisha=merchandise,
            shipping_poisha=ship_poisha,
            total_poisha=merchandise + ship_poisha,
            ready=ready,
            blockers=blockers,
            quoted_at=datetime.now(UTC),
            place_order_available=False,
        )

    async def _resolve_address(
        self, user_id: UUID, body: CheckoutQuoteIn
    ) -> CheckoutAddressSnapshotOut:
        if body.address_id is not None:
            row = await self.addresses.get_owned(user_id, body.address_id)
            return CheckoutAddressSnapshotOut(
                id=row.id,
                label=row.label,
                line1=row.line1,
                line2=row.line2,
                city=row.city,
                district=row.district,
                postal_code=row.postal_code,
                country=row.country,
                phone=row.phone,
            )

        if not body.line1 or not body.city:
            raise ProblemError(
                422,
                "Validation error",
                "Provide address_id or line1 and city.",
                PROBLEM_VALIDATION,
            )
        return CheckoutAddressSnapshotOut(
            label=body.label,
            line1=body.line1.strip(),
            line2=body.line2.strip() if body.line2 else None,
            city=body.city.strip(),
            district=body.district.strip() if body.district else None,
            postal_code=body.postal_code.strip() if body.postal_code else None,
            country=(body.country or "BD").upper(),
            phone=body.phone.strip() if body.phone else None,
        )

    def _stock_lines(self, cart: CartOut) -> list[CheckoutStockLineOut]:
        lines: list[CheckoutStockLineOut] = []
        for item in cart.items:
            available = item.qty_available
            ok = True
            message: str | None = None
            # Soft stock: only enforce when ledger shows positive on-hand.
            if available is not None and available > 0 and item.qty > available:
                ok = False
                message = f"Only {available} in stock."
            elif available == 0:
                message = "Stock not tracked or currently zero."
            lines.append(
                CheckoutStockLineOut(
                    variant_id=item.variant_id,
                    sku=item.sku,
                    qty=item.qty,
                    qty_available=available,
                    ok=ok,
                    message=message,
                )
            )
        return lines
