from datetime import datetime, timedelta
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

OUTPUT_DIR = Path("generated")

INVOICE_TOOL_SCHEMA = {
    "name": "create_invoice",
    "description": (
        "Generate a real PDF invoice for a client with one or more line items. "
        "This creates an actual file, so it should only run after the user confirms."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "client_name": {"type": "string", "description": "Name of the client being billed"},
            "items": {
                "type": "array",
                "description": "Line items on the invoice",
                "items": {
                    "type": "object",
                    "properties": {
                        "description": {"type": "string"},
                        "quantity": {"type": "number"},
                        "unit_price": {"type": "number"},
                    },
                    "required": ["description", "quantity", "unit_price"],
                },
            },
            "due_in_days": {"type": "integer", "description": "Days until payment is due", "default": 30},
            "tax_rate": {"type": "number", "description": "Tax rate as a decimal, e.g. 0.07 for 7%", "default": 0.0},
        },
        "required": ["client_name", "items"],
    },
    "requires_confirmation": True,
}


def create_invoice(client_name: str, items: list[dict], due_in_days: int = 30, tax_rate: float = 0.0) -> dict:
    OUTPUT_DIR.mkdir(exist_ok=True)

    invoice_number = f"INV-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    subtotal = sum(i["quantity"] * i["unit_price"] for i in items)
    tax_amount = subtotal * tax_rate
    total = subtotal + tax_amount
    due_date = (datetime.now() + timedelta(days=due_in_days)).strftime("%B %d, %Y")

    out_path = OUTPUT_DIR / f"{invoice_number}.pdf"
    _draw_invoice(out_path, invoice_number, client_name, items, subtotal, tax_rate, tax_amount, total, due_date)

    return {
        "invoice_number": invoice_number,
        "client_name": client_name,
        "subtotal": round(subtotal, 2),
        "tax": round(tax_amount, 2),
        "total": round(total, 2),
        "due_date": due_date,
        "file_path": str(out_path),
    }


def _draw_invoice(out_path, invoice_number, client_name, items, subtotal, tax_rate, tax_amount, total, due_date):
    page_w, page_h = A4
    margin = 20 * mm
    accent = colors.HexColor("#4338CA")

    c = canvas.Canvas(str(out_path), pagesize=A4)
    y = page_h - margin

    c.setFillColor(colors.HexColor("#17140F"))
    c.setFont("Helvetica-Bold", 22)
    c.drawString(margin, y, "INVOICE")
    c.setFont("Helvetica", 9)
    c.setFillColor(colors.HexColor("#5C574C"))
    c.drawRightString(page_w - margin, y, f"# {invoice_number}")
    y -= 10 * mm

    c.drawString(margin, y, f"Bill to: {client_name}")
    c.drawRightString(page_w - margin, y, f"Due: {due_date}")
    y -= 12 * mm

    c.setFillColor(accent)
    c.rect(margin, y - 5 * mm, page_w - 2 * margin, 7 * mm, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(margin + 2 * mm, y - 2 * mm, "DESCRIPTION")
    c.drawRightString(page_w - margin, y - 2 * mm, "TOTAL")
    y -= 12 * mm

    for item in items:
        line_total = item["quantity"] * item["unit_price"]
        c.setFillColor(colors.HexColor("#17140F"))
        c.setFont("Helvetica", 9)
        c.drawString(margin + 2 * mm, y, f"{item['description']} (x{item['quantity']})")
        c.drawRightString(page_w - margin, y, f"${line_total:,.2f}")
        y -= 8 * mm

    y -= 4 * mm
    c.setStrokeColor(colors.HexColor("#E7E2D6"))
    c.line(margin, y, page_w - margin, y)
    y -= 8 * mm

    c.setFont("Helvetica", 9)
    c.setFillColor(colors.HexColor("#5C574C"))
    c.drawRightString(page_w - margin - 30 * mm, y, "Subtotal")
    c.setFillColor(colors.HexColor("#17140F"))
    c.drawRightString(page_w - margin, y, f"${subtotal:,.2f}")
    y -= 6 * mm

    if tax_rate > 0:
        c.setFillColor(colors.HexColor("#5C574C"))
        c.drawRightString(page_w - margin - 30 * mm, y, f"Tax ({tax_rate * 100:.0f}%)")
        c.setFillColor(colors.HexColor("#17140F"))
        c.drawRightString(page_w - margin, y, f"${tax_amount:,.2f}")
        y -= 6 * mm

    c.setFillColor(accent)
    c.roundRect(page_w - margin - 60 * mm, y - 3 * mm, 60 * mm, 9 * mm, 2 * mm, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 10)
    c.drawRightString(page_w - margin - 30 * mm, y, "TOTAL")
    c.drawRightString(page_w - margin, y, f"${total:,.2f}")

    c.save()