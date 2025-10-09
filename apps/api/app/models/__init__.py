"""ORM models. Import side effects register tables on Base.metadata."""

from app.models.address import Address
from app.models.audit import AuditLog
from app.models.catalog import Attribute, Category, CategoryAttribute
from app.models.product import Product, ProductAttribute, ProductVariant
from app.models.role import Role, UserRole
from app.models.staff import RecoveryCode, StaffPermission
from app.models.token import EmailVerificationToken, PasswordResetToken, RefreshToken
from app.models.user import User

__all__ = [
    "Address",
    "Attribute",
    "AuditLog",
    "Category",
    "CategoryAttribute",
    "EmailVerificationToken",
    "PasswordResetToken",
    "Product",
    "ProductAttribute",
    "ProductVariant",
    "RecoveryCode",
    "RefreshToken",
    "Role",
    "StaffPermission",
    "User",
    "UserRole",
]
