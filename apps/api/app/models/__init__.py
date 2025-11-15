"""ORM models. Import side effects register tables on Base.metadata."""

from app.models.address import Address
from app.models.audit import AuditLog
from app.models.cart import Cart, CartItem
from app.models.catalog import Attribute, Category, CategoryAttribute
from app.models.inventory import StockBatch, StockMovement
from app.models.order import Order, OrderEvent, OrderItem
from app.models.product import Product, ProductAttribute, ProductImage, ProductVariant
from app.models.reservation import StockReservationAllocation
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
    "DeliveryWeightTier",
    "DeliveryZone",
    "EmailVerificationToken",
    "Order",
    "OrderEvent",
    "OrderItem",
    "PasswordResetToken",
    "Product",
    "ProductAttribute",
    "ProductImage",
    "ProductVariant",
    "RecoveryCode",
    "RefreshToken",
    "Role",
    "StaffPermission",
    "StockBatch",
    "StockMovement",
    "StockReservationAllocation",
    "User",
    "UserRole",
]
