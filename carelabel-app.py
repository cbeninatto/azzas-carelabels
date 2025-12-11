from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from io import BytesIO
from pathlib import Path

# ASSETS_DIR, BRAND_LOGOS and CARE_ICONS_PATH stay as you already have


def create_carelabel_pdf(brand: str, full_text: str) -> bytes:
    """
    Single-page carelabel PDF:

    • Physical size: 30 x 80 mm (W x H)
    • Logo centered at the top in a fixed band
    • Text block with font size tuned to match reference
    • Care icons at the bottom with fixed visual size
    """

    # --- Page size (matches 80x30 mm carelabel) ---
    width = 30 * mm   # W
    height = 80 * mm  # H

    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=(width, height))

    # --- Outer border ---
    border_margin = 0.5 * mm
    c.setLineWidth(0.5)
    c.rect(
        border_margin,
        border_margin,
        width - 2 * border_margin,
        height - 2 * border_margin,
    )

    inner_margin_x = 3 * mm

    # --- Logo band (top) ---
    top_margin = 3 * mm          # distance from top border
    logo_max_height = 14 * mm    # height of logo band
    logo_max_width = width - 2 * inner_margin_x

    logo_path: Path | None = BRAND_LOGOS.get(brand)
    if logo_path and logo_path.exists():
        logo_img = ImageReader(str(logo_path))
        iw, ih = logo_img.getSize()
        scale = min(logo_max_width / iw, logo_max_height / ih)
        draw_w = iw * scale
        draw_h = ih * scale

        x_logo = (width - draw_w) / 2.0
        y_logo = height - top_margin - draw_h

        c.drawImage(
            logo_img,
            x_logo,
            y_logo,
            width=draw_w,
            height=draw_h,
            preserveAspectRatio=True,
            mask="auto",
        )
        # Text starts a bit below the logo
        text_top_y = y_logo - 2 * mm
    else:
        # If logo not found, reserve same band anyway
        text_top_y = height - (top_margin + logo_max_height + 2 * mm)

    # --- Care icons (bottom) ---
    icons_bottom_margin = 3 * mm
    icons_max_height = 7 * mm          # controls icon height (match reference)
    icons_max_width = width - 8 * mm   # leaves some side margin

    text_bottom_limit = icons_bottom_margin  # fallback if no icons

    if CARE_ICONS_PATH.exists():
        icons_img = ImageReader(str(CARE_ICONS_PATH))
        iw, ih = icons_img.getSize()
        scale_i = min(icons_max_width / iw, icons_max_height / ih)
        draw_w_i = iw * scale_i
        draw_h_i = ih * scale_i

        x_icons = (width - draw_w_i) / 2.0
        y_icons = icons_bottom_margin  # fixed distance from bottom border

        c.drawImage(
            icons_img,
            x_icons,
            y_icons,
            width=draw_w_i,
            height=draw_h_i,
            preserveAspectRatio=True,
            mask="auto",
        )

        # Text must stay above the icon band
        text_bottom_limit = y_icons + draw_h_i + 2 * mm

    # --- Text block (middle) ---
    font_size = 7          # tuned to look like the sample
    leading = 8            # line spacing (points)

    text_obj = c.beginText()
    text_obj.setFont("Helvetica", font_size)
    text_obj.setLeading(leading)
    text_obj.setTextOrigin(inner_margin_x, text_top_y)

    for line in full_text.splitlines():
        # Stop if we are about to overlap the icons
        if text_obj.getY() <= text_bottom_limit:
            break
        text_obj.textLine(line)

    c.drawText(text_obj)

    c.showPage()
    c.save()
    pdf_bytes = buf.getvalue()
    buf.close()
    return pdf_bytes
