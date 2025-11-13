"""Order statuses and allowed transitions (Part 17 core)."""

ORDER_STATUSES = frozenset(
    {
        "pending_payment",
        "confirmed",
        "shipped",
        "delivered",
        "cancelled",
    }
)

# from_status -> allowed to_status values
ALLOWED_TRANSITIONS: dict[str, frozenset[str]] = {
    "pending_payment": frozenset({"confirmed", "cancelled"}),
    "confirmed": frozenset({"shipped", "cancelled"}),
    "shipped": frozenset({"delivered"}),
}

CUSTOMER_CANCEL_STATUSES = frozenset({"pending_payment", "confirmed"})

ADMIN_LIST_FILTERS = frozenset(
    {"pending_payment", "confirmed", "shipped", "delivered", "cancelled", "all"}
)

PAYMENT_METHODS = frozenset({"cod", "bkash", "sslcommerz"})
