"""Allowed attribute kinds and default skincare seed data."""

ATTRIBUTE_KINDS = frozenset({"skin_type", "concern", "ingredient", "texture", "claim"})

DEFAULT_SKIN_TYPES: list[tuple[str, str, int]] = [
    ("dry", "Dry", 10),
    ("oily", "Oily", 20),
    ("combination", "Combination", 30),
    ("sensitive", "Sensitive", 40),
    ("acne-prone", "Acne-prone", 50),
]

DEFAULT_CONCERNS: list[tuple[str, str, int]] = [
    ("acne", "Acne", 10),
    ("pigmentation", "Pigmentation", 20),
    ("aging", "Aging", 30),
    ("barrier", "Barrier", 40),
    ("hydration", "Hydration", 50),
]

DEFAULT_INGREDIENTS: list[tuple[str, str, int]] = [
    ("niacinamide", "Niacinamide", 10),
    ("hyaluronic-acid", "Hyaluronic acid", 20),
    ("retinol", "Retinol", 30),
    ("vitamin-c", "Vitamin C", 40),
    ("ceramides", "Ceramides", 50),
    ("salicylic-acid", "Salicylic acid", 60),
    ("centella", "Centella asiatica", 70),
    ("peptides", "Peptides", 80),
]

DEFAULT_TEXTURES: list[tuple[str, str, int]] = [
    ("gel", "Gel", 10),
    ("cream", "Cream", 20),
    ("serum-texture", "Serum", 30),
    ("oil", "Oil", 40),
    ("balm", "Balm", 50),
]

DEFAULT_CLAIMS: list[tuple[str, str, int]] = [
    ("fragrance-free", "Fragrance-free", 10),
    ("cruelty-free", "Cruelty-free", 20),
    ("vegan", "Vegan", 30),
]

# (slug, name, sort_order, description)
DEFAULT_LEAF_CATEGORIES: list[tuple[str, str, int, str]] = [
    ("cleanser", "Cleanser", 10, "Face washes and cleansing balms."),
    ("toner", "Toner", 20, "Toners and essences."),
    ("serum", "Serum", 30, "Targeted treatment serums."),
    ("moisturizer", "Moisturizer", 40, "Creams, gels, and lotions."),
    ("sunscreen", "Sunscreen", 50, "Daily UV protection."),
    ("mask", "Mask", 60, "Sheet, clay, and overnight masks."),
    ("lip", "Lip", 70, "Lip balms and treatments."),
    ("kits", "Kits", 80, "Routines and gift sets."),
]
