"""Build a simple PDF invoice with reportlab."""

from __future__ import annotations

from io import BytesIO
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas


def _bdt(poisha: int) -> str:
    return f"BDT {poisha / 100:.2f}"


def build_invoice_pdf(
    *,
    order_number: str,
    placed_at: str,
    ship_to: str,
    payment_method: str | None,
    payment_status: str | None,
    items: list[dict[str, Any]],
    merchandise_poisha: int,
    shipping_poisha: int,
    total_poisha: int,
    refunds_poisha: int = 0,
) -> bytes:
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    y = height - 20 * mm

    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(20 * mm, y, "Solum")
    y -= 8 * mm
    pdf.setFont("Helvetica", 11)
    pdf.drawString(20 * mm, y, f"Invoice · {order_number}")
    y -= 6 * mm
    pdf.drawString(20 * mm, y, f"Placed: {placed_at}")
    y -= 6 * mm
    pdf.drawString(20 * mm, y, f"Ship to: {ship_to}")
    y -= 6 * mm
    pdf.drawString(
        20 * mm,
        y,
        f"Payment: {payment_method or '—'} · {payment_status or '—'}",
    )
    y -= 10 * mm

    pdf.setStrokeColor(colors.grey)
    pdf.line(20 * mm, y, width - 20 * mm, y)
    y -= 8 * mm
    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawString(20 * mm, y, "Item")
    pdf.drawString(110 * mm, y, "Qty")
    pdf.drawRightString(width - 20 * mm, y, "Line")
    y -= 6 * mm
    pdf.setFont("Helvetica", 10)
    for item in items:
        if y < 30 * mm:
            pdf.showPage()
            y = height - 20 * mm
            pdf.setFont("Helvetica", 10)
        pdf.drawString(20 * mm, y, str(item["name"])[:48])
        pdf.drawString(110 * mm, y, str(item["qty"]))
        pdf.drawRightString(width - 20 * mm, y, _bdt(int(item["line_total_poisha"])))
        y -= 5 * mm

    y -= 4 * mm
    pdf.line(20 * mm, y, width - 20 * mm, y)
    y -= 7 * mm
    pdf.drawRightString(width - 20 * mm, y, f"Merchandise {_bdt(merchandise_poisha)}")
    y -= 5 * mm
    pdf.drawRightString(width - 20 * mm, y, f"Shipping {_bdt(shipping_poisha)}")
    y -= 5 * mm
    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawRightString(width - 20 * mm, y, f"Total {_bdt(total_poisha)}")
    if refunds_poisha > 0:
        y -= 6 * mm
        pdf.setFont("Helvetica", 10)
        pdf.drawRightString(width - 20 * mm, y, f"Refunds {_bdt(refunds_poisha)}")

    pdf.showPage()
    pdf.save()
    return buffer.getvalue()
