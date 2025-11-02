"""Cart status and routine-upsell helpers."""

CART_STATUSES = frozenset({"active", "abandoned", "converted", "cleared"})
ADMIN_LIST_FILTERS = frozenset({"active", "abandoned", "cleared", "all"})

# Ordered skincare steps used for “complete the routine” suggestions.
ROUTINE_CATEGORY_SLUGS = (
    "cleanser",
    "toner",
    "serum",
    "moisturizer",
    "sunscreen",
)
