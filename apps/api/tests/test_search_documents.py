"""Search document builder."""

from types import SimpleNamespace
from uuid import uuid4

from app.search.documents import product_document


def test_product_document_published_with_facets() -> None:
    product_id = uuid4()
    row = SimpleNamespace(
        id=product_id,
        slug="niacinamide-serum",
        name="Niacinamide Serum",
        subtitle="Barrier support",
        description="Daily serum",
        ingredients_text="Niacinamide, Zinc",
        routine_step="am",
        status="published",
        deleted_at=None,
        published_at=None,
        category=SimpleNamespace(slug="serum", name="Serum"),
        attributes=[
            SimpleNamespace(kind="concern", slug="barrier", is_active=True),
            SimpleNamespace(kind="ingredient", slug="niacinamide", is_active=True),
            SimpleNamespace(kind="skin_type", slug="oily", is_active=True),
            SimpleNamespace(kind="ingredient", slug="inactive-ing", is_active=False),
        ],
        variants=[
            SimpleNamespace(is_active=True, price_poisha=120000),
            SimpleNamespace(is_active=False, price_poisha=90000),
        ],
    )
    doc = product_document(row)  # type: ignore[arg-type]
    assert doc is not None
    assert doc["id"] == str(product_id)
    assert doc["from_price_poisha"] == 120000
    assert doc["concerns"] == ["barrier"]
    assert doc["ingredients"] == ["niacinamide"]
    assert doc["skin_types"] == ["oily"]


def test_product_document_skips_drafts() -> None:
    row = SimpleNamespace(
        id=uuid4(),
        slug="draft",
        name="Draft",
        subtitle=None,
        description=None,
        ingredients_text=None,
        routine_step=None,
        status="draft",
        deleted_at=None,
        published_at=None,
        category=None,
        attributes=[],
        variants=[],
    )
    assert product_document(row) is None  # type: ignore[arg-type]
