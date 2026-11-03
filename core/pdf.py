from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

TEAL = colors.HexColor("#0f766e")


def build_bill_pdf(order):
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm,
                            topMargin=16 * mm, bottomMargin=16 * mm,
                            title=f"Food Bridge Bill #{order.pk}")
    styles = getSampleStyleSheet()
    h1 = ParagraphStyle("h1", parent=styles["Title"], textColor=TEAL, alignment=0, fontSize=24)
    body = styles["BodyText"]
    small = ParagraphStyle("small", parent=body, fontSize=9, textColor=colors.grey)

    story = [Paragraph("Food Bridge", h1),
             Paragraph(f"Order bill #{order.pk}", styles["Heading2"]), Spacer(1, 4 * mm)]

    info = [
        ["Convention hall", order.hall.name, "Restaurant", order.restaurant.name],
        ["Event date", order.event_date.strftime("%d %b %Y"), "Guests", str(order.guests)],
        ["Hall address", order.hall.location_text, "Restaurant address", order.restaurant.location_text],
        ["Status", order.get_status_display(), "Ordered on", order.created_at.strftime("%d %b %Y")],
    ]
    info = [[Paragraph(escape(c), body) for c in row] for row in info]
    t = Table(info, colWidths=[28 * mm, 58 * mm, 32 * mm, 54 * mm])
    t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"),
                           ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#ecfdf5")),
                           ("BACKGROUND", (2, 0), (2, -1), colors.HexColor("#ecfdf5")),
                           ("GRID", (0, 0), (-1, -1), 0.4, colors.lightgrey)]))
    story += [t, Spacer(1, 8 * mm)]

    rows = [["#", "Item", "Per person", "Total qty", "Unit price", "Amount"]]
    for i, it in enumerate(order.items.all(), 1):
        rows.append([str(i), Paragraph(escape(it.name), body), str(it.per_person), str(it.total_qty),
                     f"{it.unit_price:,.2f}", f"{it.line_total:,.2f}"])
    rows.append(["", "", "", "", "Grand total (BDT)", f"{order.total:,.2f}"])
    t = Table(rows, colWidths=[10 * mm, 62 * mm, 22 * mm, 22 * mm, 30 * mm, 28 * mm], repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), TEAL), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ALIGN", (2, 0), (-1, -1), "RIGHT"), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -2), 0.4, colors.lightgrey),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#fef3c7")),
        ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story += [t, Spacer(1, 10 * mm),
              Paragraph("Thank you for using Food Bridge - connecting surplus kitchens with the people who need meals.", small)]
    doc.build(story)
    return buf.getvalue()
