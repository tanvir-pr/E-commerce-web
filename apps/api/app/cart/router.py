"""Customer cart routes (guest cookie or signed-in user)."""

from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.cart.schemas import CartItemIn, CartItemPatchIn, CartOut, UpsellOut
from app.cart.service import CartService
from app.config import get_settings
from app.deps import get_optional_user_id
from app.security.cookies import CART_COOKIE, clear_cart_cookie, set_cart_cookie
from app.session import get_session

router = APIRouter(prefix="/cart", tags=["cart"])


def get_cart_service(session: AsyncSession = Depends(get_session)) -> CartService:
    return CartService(session)


def _guest_token(request: Request) -> str | None:
    return request.cookies.get(CART_COOKIE)


def _apply_guest_cookie(response: Response, token: str | None) -> None:
    if not token:
        return
    settings = get_settings()
    set_cart_cookie(
        response,
        token,
        max_age=settings.cart_guest_cookie_max_age_days * 24 * 60 * 60,
    )


@router.get("", response_model=CartOut)
async def get_cart(
    request: Request,
    response: Response,
    user_id: UUID | None = Depends(get_optional_user_id),
    service: CartService = Depends(get_cart_service),
) -> CartOut:
    cart, new_token = await service.get_cart(
        user_id=user_id, guest_token=_guest_token(request)
    )
    if user_id is not None:
        clear_cart_cookie(response)
    else:
        _apply_guest_cookie(response, new_token)
    return cart


@router.post("/items", response_model=CartOut, status_code=201)
async def add_cart_item(
    body: CartItemIn,
    request: Request,
    response: Response,
    user_id: UUID | None = Depends(get_optional_user_id),
    service: CartService = Depends(get_cart_service),
) -> CartOut:
    cart, new_token = await service.add_item(
        body, user_id=user_id, guest_token=_guest_token(request)
    )
    if user_id is not None:
        clear_cart_cookie(response)
    else:
        _apply_guest_cookie(response, new_token)
    return cart


@router.patch("/items/{item_id}", response_model=CartOut)
async def patch_cart_item(
    item_id: UUID,
    body: CartItemPatchIn,
    request: Request,
    response: Response,
    user_id: UUID | None = Depends(get_optional_user_id),
    service: CartService = Depends(get_cart_service),
) -> CartOut:
    cart, new_token = await service.patch_item(
        item_id, body, user_id=user_id, guest_token=_guest_token(request)
    )
    if user_id is not None:
        clear_cart_cookie(response)
    else:
        _apply_guest_cookie(response, new_token)
    return cart


@router.delete("/items/{item_id}", response_model=CartOut)
async def delete_cart_item(
    item_id: UUID,
    request: Request,
    response: Response,
    user_id: UUID | None = Depends(get_optional_user_id),
    service: CartService = Depends(get_cart_service),
) -> CartOut:
    cart, new_token = await service.remove_item(
        item_id, user_id=user_id, guest_token=_guest_token(request)
    )
    if user_id is not None:
        clear_cart_cookie(response)
    else:
        _apply_guest_cookie(response, new_token)
    return cart


@router.delete("", response_model=CartOut)
async def clear_cart(
    request: Request,
    response: Response,
    user_id: UUID | None = Depends(get_optional_user_id),
    service: CartService = Depends(get_cart_service),
) -> CartOut:
    cart, new_token = await service.clear_own(
        user_id=user_id, guest_token=_guest_token(request)
    )
    if user_id is not None:
        clear_cart_cookie(response)
    else:
        _apply_guest_cookie(response, new_token)
    return cart


@router.get("/upsell", response_model=UpsellOut)
async def cart_upsell(
    request: Request,
    response: Response,
    user_id: UUID | None = Depends(get_optional_user_id),
    service: CartService = Depends(get_cart_service),
) -> UpsellOut:
    # Ensure cart cookie exists for guests so subsequent adds share the cart.
    _, new_token = await service.resolve_cart(
        user_id=user_id, guest_token=_guest_token(request)
    )
    if user_id is None:
        _apply_guest_cookie(response, new_token)
    else:
        clear_cart_cookie(response)
    return await service.upsell(user_id=user_id, guest_token=_guest_token(request) or new_token)
