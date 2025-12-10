"""ORM models. Import side effects register tables on Base.metadata."""

from app.models.address import Address
from app.models.audit import AuditLog
from app.models.cart import Cart, CartItem
from app.models.catalog import Attribute, Category, CategoryAttribute
from app.models.coupon import Coupon, CouponRedemption
from app.models.inventory import StockBatch, StockMovement
from app.models.order import Order, OrderEvent, OrderItem
from app.models.payment import PaymentEvent
from app.models.product import Product, ProductAttribute, ProductImage, ProductVariant
from app.models.reservation import StockReservationAllocation
from app.models.returns import (
    LedgerEntry,
    ReturnRequest,
    ReturnRequestItem,
    ReturnRequestPhoto,
)
from app.models.review import ProductReview, WishlistItem
from app.models.role import Role, UserRole
from app.models.shipping import DeliveryWeightTier, DeliveryZone
from app.models.staff import RecoveryCode, StaffPermission
from app.models.token import EmailVerificationToken, PasswordResetToken, RefreshToken
from app.models.user import User

__all__ = [
    "Address",
    "Attribute",
    "AuditLog",
    "Cart",
    "CartItem",
    "Category",
    "CategoryAttribute",
    "Coupon",
    "CouponRedemption",
    "DeliveryWeightTier",
    "DeliveryZone",
    "EmailVerificationToken",
    "LedgerEntry",
    "Order",
    "OrderEvent",
    "OrderItem",
    "PasswordResetToken",
    "PaymentEvent",
    "Product",
    "ProductAttribute",
    "ProductImage",
    "ProductReview",
    "ProductVariant",
    "RecoveryCode",
    "RefreshToken",
    "ReturnRequest",
    "ReturnRequestItem",
    "ReturnRequestPhoto",
    "Role",
    "StaffPermission",
    "StockBatch",
    "StockMovement",
    "StockReservationAllocation",
    "User",
    "UserRole",
    "WishlistItem",
]
