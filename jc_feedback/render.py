import textwrap

import qrcode
from reportlab.graphics import renderPDF
from reportlab.graphics.barcode import qr
from reportlab.graphics.shapes import Drawing
from reportlab.lib.colors import HexColor, black
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

GREY = HexColor("#555555")
LIGHT = HexColor("#BBBBBB")
PAGE_W, PAGE_H = A4
LEFT, RIGHT = 15 * mm, PAGE_W - 15 * mm


def draw_qr(c, url, x, y, size):
    widget = qr.QrCodeWidget(url, barLevel="L", barBorder=2)
    x0, y0, x1, y1 = widget.getBounds()
    d = Drawing(size, size, transform=[size / (x1 - x0), 0, 0, size / (y1 - y0), 0, 0])
    d.add(widget)
    renderPDF.draw(d, c, x, y)


def draw_scale_row(c, text, y, low, high):
    c.setFont("Helvetica", 10)
    c.drawString(LEFT, y, text)
    n = high - low + 1
    box, gap = 5.5 * mm, 4 * mm
    x = RIGHT - n * box - (n - 1) * gap
    for v in range(low, high + 1):
        c.rect(x, y - 1.5 * mm, box, box)
        c.setFont("Helvetica", 7)
        c.setFillColor(GREY)
        c.drawCentredString(x + box / 2, y - 5 * mm, str(v))
        c.setFillColor(black)
        x += box + gap


def split_title(c, title, width_first, width_second, size=10):
    # Shrink until the title fits on the two Paper lines.
    while size > 6:
        words, line1 = title.split(), ""
        while words and c.stringWidth(f"{line1} {words[0]}".strip(), "Helvetica-Bold", size) <= width_first:
            line1 = f"{line1} {words.pop(0)}".strip()
        line2 = " ".join(words)
        if c.stringWidth(line2, "Helvetica-Bold", size) <= width_second:
            return line1, line2, size
        size -= 0.5
    return line1, textwrap.shorten(line2, 120), size


def draw_header(c, y, pc, title, date_str, ink):
    c.setFont("Helvetica-Bold", 14)
    c.drawString(LEFT, y, pc["heading"])
    c.setFont("Helvetica-Oblique", 8.5)
    c.setFillColor(GREY)
    c.drawString(LEFT, y - 5 * mm, pc["note"])
    c.setFillColor(black)

    c.setFont("Helvetica", 9.5)
    dx = RIGHT - 45 * mm
    c.drawString(dx, y, "Date:")
    d0 = dx + c.stringWidth("Date:", "Helvetica", 9.5) + 2 * mm
    c.line(d0, y - 1, RIGHT, y - 1)
    c.setFont("Helvetica-Bold", 10)
    c.setFillColor(ink)
    c.drawString(d0 + 1 * mm, y + 0.5 * mm, date_str)
    c.setFillColor(black)

    y -= 13 * mm
    c.setFont("Helvetica", 9.5)
    c.drawString(LEFT, y, "Paper:")
    p0 = LEFT + c.stringWidth("Paper:", "Helvetica", 9.5) + 2 * mm
    c.line(p0, y - 1, RIGHT, y - 1)
    c.line(LEFT, y - 7 * mm - 1, RIGHT, y - 7 * mm - 1)
    l1, l2, size = split_title(c, title, RIGHT - p0 - 2 * mm, RIGHT - LEFT - 2 * mm)
    c.setFont("Helvetica-Bold", size)
    c.setFillColor(ink)
    c.drawString(p0 + 1 * mm, y + 0.5 * mm, l1)
    c.drawString(LEFT + 1 * mm, y - 7 * mm + 0.5 * mm, l2)
    c.setFillColor(black)
    return y - 7 * mm


def draw_form(c, y_top, cfg, url, title, date_str):
    pc, sc = cfg["print"], cfg["scale"]
    ink = HexColor(pc["text_color"])
    scales = [q for q in cfg["questions"] if q["kind"] == "scale"]
    comment = next((q for q in cfg["questions"] if q["kind"] == "paragraph"), None)

    y = draw_header(c, y_top - 11 * mm, pc, title, date_str, ink)

    y -= 7 * mm
    c.setFont("Helvetica-Oblique", 8)
    c.setFillColor(GREY)
    c.drawRightString(RIGHT, y, f"{sc['low']} = {sc['low_label']}     {sc['high']} = {sc['high_label']}")
    c.setFillColor(black)

    # Row spacing shrinks when more questions are added, so the form stays a half page.
    n_sections = len({q.get("section") for q in scales})
    step = min(11 * mm, (69 * mm - n_sections * 7 * mm) / max(len(scales), 1))
    section = None
    for k, q in enumerate(scales, start=1):
        if q.get("section") != section:
            section = q.get("section")
            y -= 6 * mm if k == 1 else 1 * mm
            c.setFont("Helvetica-Bold", 10)
            c.drawString(LEFT, y, section or "")
            y -= 7 * mm
        draw_scale_row(c, f"{k}.  {q['title']}", y, sc["low"], sc["high"])
        y -= step

    qr_size = pc["qr_size_mm"] * mm
    y -= 3 * mm
    c.setFont("Helvetica-Bold", 10)
    c.drawString(LEFT, y, comment["title"] + ":" if comment else "")
    for _ in range(pc["comment_lines"]):
        y -= 7 * mm
        c.setStrokeColor(LIGHT)
        c.line(LEFT, y, RIGHT - qr_size - 8 * mm, y)
    c.setStrokeColor(black)

    qx, qy = RIGHT - qr_size, y - 5 * mm
    draw_qr(c, url, qx, qy, qr_size)
    c.setFont("Helvetica", 7)
    c.drawCentredString(qx + qr_size / 2, qy + qr_size + 1.5 * mm, "Prefer typing?")
    c.drawCentredString(qx + qr_size / 2, qy - 2.5 * mm, "Scan - fully anonymous")


def make_pdf(path, cfg, url, title, date_str):
    c = canvas.Canvas(str(path), pagesize=A4)
    c.setTitle(f"GW JC Feedback - {date_str}")
    draw_form(c, PAGE_H, cfg, url, title, date_str)
    c.setDash(4, 3)
    c.setStrokeColor(LIGHT)
    c.line(8 * mm, PAGE_H / 2, PAGE_W - 8 * mm, PAGE_H / 2)
    c.setDash()
    c.setStrokeColor(black)
    draw_form(c, PAGE_H / 2, cfg, url, title, date_str)
    c.save()


def make_png(path, url):
    qrcode.make(url, border=4, box_size=10, error_correction=qrcode.constants.ERROR_CORRECT_L).save(path)
