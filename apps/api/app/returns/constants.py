"""RMA and ledger constants."""

RETURN_STATUSES = frozenset({"pending", "approved", "rejected", "cancelled"})
RETURN_REASON_CODES = frozenset(
    {"wrong_item", "defective", "unopened", "other"}
)
LEDGER_ENTRY_TYPES = frozenset({"sale", "refund", "shipping_refund"})
MAX_RETURN_PHOTOS = 3
RETURNABLE_PAYMENT_STATUSES = frozenset({"paid", "collected"})
