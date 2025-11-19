"""Order statuses and allowed transitions."""

ORDER_STATUSES = frozenset(
    {
        "pending_payment",
        "confirmed",
        "shipped",
        "delivered",
        "delivery_failed",
        "returned",
        "cancelled",
    }
)

# from_status -> allowed to_status values
ALLOWED_TRANSITIONS: dict[str, frozenset[str]] = {
    "pending_payment": frozenset({"confirmed", "cancelled"}),
    "confirmed": frozenset({"shipped", "cancelled"}),
    "shipped": frozenset({"delivered", "delivery_failed", "returned"}),
    "delivery_failed": frozenset({"shipped", "returned"}),
}

# Part 19: customer + staff may cancel until the parcel ships.
CUSTOMER_CANCEL_STATUSES = frozenset({"pending_payment", "confirmed"})
STAFF_CANCEL_STATUSES = frozenset({"pending_payment", "confirmed"})

ADMIN_LIST_FILTERS = frozenset(
    {
        "pending_payment",
        "confirmed",
        "shipped",
        "delivered",
        "delivery_failed",
        "returned",
        "cancelled",
        "all",
    }
)

PAYMENT_METHODS = frozenset({"cod", "bkash", "sslcommerz"})
PAYMENT_STATUSES = frozenset(
    {
        "pending",
        "cod_pending",
        "collected",
        "paid",
        "cancelled",
        "refunded",
    }
)
