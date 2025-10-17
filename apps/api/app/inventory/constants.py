"""Stock movement reasons."""

MOVEMENT_REASONS = frozenset(
    {
        "receipt",
        "adjustment_in",
        "adjustment_out",
        "waste",
        "recount",
        "fefo_issue",
    }
)
