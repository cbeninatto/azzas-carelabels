import re
import math
import base64
from io import BytesIO
from pathlib import Path

import streamlit as st
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase.pdfmetrics import stringWidth


# ---------------- BASIC CONFIG ----------------

st.set_page_config(
    page_title="Carelabel & SKU Label Generator",
    layout="wide",
)

ASSETS_DIR = Path("assets")

BRAND_LOGOS = {
    "Arezzo": ASSETS_DIR / "logo_arezzo.png",
    "Anacapri": ASSETS_DIR / "logo_anacapri.png",
    "Schutz": ASSETS_DIR / "logo_schutz.png",
    "Reserva": ASSETS_DIR / "logo_reserva.png",
}

CARE_ICONS_PATH = ASSETS_DIR / "carelabel_icons.png"


# ---------------- IMAGE HELPERS ----------------

def load_image_base64(path: Path):
    if not path.exists():
        return None
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


BRAND_LOGOS_B64 = {name: load_image_base64(p) for name, p in BRAND_LOGOS.items()}
CARE_ICONS_B64 = load_image_base64(CARE_ICONS_PATH)


# ---------------- TRANSLATION / TEXT ----------------

REPLACEMENTS = [
    (r"polyvinyl chloride\s*\(?\s*pvc\s*\)?", "POLICLORETO DE VINILA (PVC)"),
    (r"\bpvc\b", "POLICLORETO DE VINILA (PVC)"),
    (r"polyurethane", "POLIURETANO (PU)"),
    (r"\bpu\b", "POLIURETANO (PU)"),
    (r"polyester", "POLIÉSTER"),
    (r"polyamide", "POLIAMIDA"),
    (r"nylon", "POLIAMIDA"),
    (r"cotton", "ALGODÃO"),
    (r"filler", "ENCHIMENTO"),
    (r"base fabric", "TECIDO BASE"),
    (r"leather", "COURO"),
    (r"metal", "METAL"),
]


def basic_translate_freeform(text: str) -> str:
    if not text:
        return ""
    result = text
    for pattern, repl in REPLACEMENTS:
        result = re.sub(pattern, repl, result, flags=re.IGNORECASE)
    return result.upper()


def parse_components_for_normalization(text: str):
    if not text:
        return []

    cleaned = text.replace("\n", " ")
    cleaned = re.sub(r"%\s*", "% ", cleaned)

    pattern = re.compile(
        r"(\d+(?:\.\d+)?)\s*%\s*([A-Za-zÀ-ÖØ-öø-ÿ ()/\-]+?)(?=(\d+(?:\.\d+)?\s*%|$))"
    )

    components = []
    for m in pattern.finditer(cleaned):
        pct = float(m.group(1))
        desc = m.group(2).strip()
        components.append((pct, desc))
    return components


def normalize_and_translate_composition(text: str) -> str:
    if not text:
        return ""

    components = parse_components_for_normalization(text)
    if not components:
        return basic_translate_freeform(text)

    main_components = []
    for pct, desc in components:
        d = desc.lower()
        if "filler" in d or "base fabric" in d or "enchimento" in d or "tecido base" in d:
            continue
        main_components.append((pct, desc))

    if not main_components:
        return basic_translate_freeform(text)

    total = sum(p for p, _ in main_components)
    if total <= 0:
        return basic_translate_freeform(text)

    floats = [p * 100.0 / total for p, _ in main_components]
    int_parts = [math.floor(f) for f in floats]
    fracs = [f - i for f, i in zip(floats, int_parts)]

    diff = 100 - sum(int_parts)
    if diff > 0:
        indices = sorted(range(len(fracs)), key=lambda i: fracs[i], reverse=True)
        for i in indices[:diff]:
            int_parts[i] += 1
    elif diff < 0:
        indices = sorted(range(len(fracs)), key=lambda i: fracs[i])
        for i in indices[: -diff]:
            int_parts[i] -= 1

    parts_pt = []
    for (_, desc), pct_int in zip(main_components, int_parts):
        material_pt = basic_translate_freeform(desc)
        parts_pt.append(f"{pct_int}% {material_pt}")

    return " ".join(parts_pt)


def translate_composition_to_pt(text: str) -> str:
    return normalize_and_translate_composition(text)


def build_carelabel_text(exterior_pt: str, forro_pt: str) -> str:
    return f"""IMPORTADO POR BTG PACTUAL
COMMODITIES SERTRADING S.A
CNPJ: 04.626.426/0007-00
DISTRIBUIDO POR:
AZZAS 2154 S.A
CNPJ: 16.590.234/0025-43

FABRICADO NA CHINA
SACAREZZO@AREZZO.COM.BR

PRODUTO DE MATERIAL SINTÉTICO
MATÉRIA-PRIMA
EXTERIOR: {exterior_pt}
FORRO: {forro_pt}

PROIBIDO LAVAR NA ÁGUA / NÃO ALVEJAR /
PROIBIDO USAR SECADOR / NÃO PASSAR
A FERRO / NÃO LAVAR A SECO /
LIMPAR COM PANO SECO"""


# ---------------- WORD WRAPPING ----------------

def wrap_line(text: str, max_width: float, font_name: str = "Helvetica", font_size: float = 4.0):
    if not text:
        return [""]

    words = text.split()
    lines = []
    current = ""

    for w in words:
        if not current:
            current = w
            continue
        candidate = current + " " + w
        if stringWidth(candidate, font_name, font_size) <= max_width:
            current = candidate
        else:
            lines.append(current)
            current = w

    if current:
        lines.append(current)

    return lines


# ---------------- PDF GENERATION ----------------

def create_carelabel_pdf(brand: str, full_text: str) -> bytes:
    width = 30 * mm
    height = 80 * mm

    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=(width, height))

    inner_margin_x = 3 * mm

    # Safe margins (stitch/fold)
    stitch_margin_mm = 7.0
    safe_top_y = height - stitch_margin_mm * mm
    safe_bottom_y = stitch_margin_mm * mm

    top_band_mm = 10.0
    icons_band_mm = 6.0

    # Logo
    logo_path = BRAND_LOGOS.get(brand)
    logo_bottom_y_for_text = safe_top_y - top_band_mm * mm

    if logo_path and logo_path.exists():
        logo_img = ImageReader(str(logo_path))
        iw, ih = logo_img.getSize()

        logo_max_height = (top_band_mm - 2.0) * mm
        logo_max_width = width - 2 * inner_margin_x

        scale = min(logo_max_width / iw, logo_max_height / ih)
        draw_w = iw * scale
        draw_h = ih * scale

        if brand == "Reserva":
            draw_w *= 1.5
            draw_h *= 1.5
            if draw_w > logo_max_width:
                factor = logo_max_width / draw_w
                draw_w *= factor
                draw_h *= factor

        gap_from_safe_top = 1.0 * mm
        y_logo = safe_top_y - gap_from_safe_top - draw_h
        x_logo = (width - draw_w) / 2.0

        c.drawImage(
            logo_img,
            x_logo,
            y_logo,
            width=draw_w,
            height=draw_h,
            preserveAspectRatio=True,
            mask="auto",
        )
        text_top_limit = y_logo - 2.0 * mm
    else:
        text_top_limit = logo_bottom_y_for_text

    # Icons
    icons_max_height = (icons_band_mm - 2.0) * mm
    icons_max_width = width - 2 * inner_margin_x

    if CARE_ICONS_PATH.exists():
        icons_img = ImageReader(str(CARE_ICONS_PATH))
        iw, ih = icons_img.getSize()
        scale_i = min(icons_max_width / iw, icons_max_height / ih)
        draw_w_i = iw * scale_i
        draw_h_i = ih * scale_i

        gap_from_safe_bottom = 1.0 * mm
        y_icons = safe_bottom_y + gap_from_safe_bottom
        x_icons = (width - draw_w_i) / 2.0

        c.drawImage(
            icons_img,
            x_icons,
            y_icons,
            width=draw_w_i,
            height=draw_h_i,
            preserveAspectRatio=True,
            mask="auto",
        )
        text_bottom_limit = y_icons + draw_h_i + 2.0 * mm
    else:
        text_bottom_limit = safe_bottom_y + icons_band_mm * mm

    # Text (wrapped + vertically centered)
    font_size = 4.0
    leading = 5.0
    max_text_width = width - 2 * inner_margin_x

    wrapped_lines = []
    for line in full_text.splitlines():
        if not line.strip():
            wrapped_lines.append("")
        else:
            wrapped_lines.extend(wrap_line(line, max_text_width, "Helvetica", font_size))

    n_lines = len(wrapped_lines) if wrapped_lines else 1
    text_height = max((n_lines - 1), 0) * leading

    available_top = text_top_limit
    available_bottom = text_bottom_limit
    available_height = available_top - available_bottom

    if available_height <= 0:
        y_start = available_top
    else:
        if text_height >= available_height:
            y_start = available_top
        else:
            y_start = available_top - (available_height - text_height) / 2.0

    text_obj = c.beginText()
    text_obj.setFont("Helvetica", font_size)
    text_obj.setLeading(leading)
    text_obj.setTextOrigin(inner_margin_x, y_start)

    for line in wrapped_lines:
        if text_obj.getY() <= text_bottom_limit:
            break
        text_obj.textLine(line)

    c.drawText(text_obj)

    c.showPage()
    c.save()

    pdf_bytes = buf.getvalue()
    buf.close()
    return pdf_bytes


def create_sku_labels_pdf(skus) -> bytes:
    """
    Multi-page PDF for SKU labels.
    Each page = 50 x 10 mm, NO box line, SKU centered, font size increased by 2pt.
    """
    width = 50 * mm
    height = 10 * mm

    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=(width, height))

    sku_font_size = 12  # was 10, now +2pt

    for sku in skus:
        sku = sku.strip()
        if not sku:
            continue

        # No border rectangle (removed)

        # Centered SKU
        c.setFont("Helvetica", sku_font_size)
        # Slight vertical optical adjustment
        c.drawCentredString(width / 2.0, height / 2.0 - (sku_font_size * 0.30), sku)

        c.showPage()

    c.save()
    pdf_bytes = buf.getvalue()
    buf.close()
    return pdf_bytes


# ---------------- HTML PREVIEWS (UI ONLY) ----------------

def carelabel_preview_html(full_text: str, brand: str) -> str:
    logo_b64 = BRAND_LOGOS_B64.get(brand)
    icons_b64 = CARE_ICONS_B64

    logo_html = (
        f'<img src="data:image/png;base64,{logo_b64}" '
        f'style="max-width:140px; max-height:90px; margin-bottom:6px;" />'
        if logo_b64
        else ""
    )

    icons_html = (
        f'<img src="data:image/png;base64,{icons_b64}" '
        f'style="width:65%; max-height:40px; margin-top:8px;" />'
        if icons_b64
        else ""
    )

    return f"""
    <div style="
        padding:8px 10px;
        width:260px;
        min-height:520px;
        font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
        ">
        <div style="text-align:center; margin-bottom:8px;">
            {logo_html}
        </div>
        <div style="font-size:9px; line-height:1.35; white-space:pre-wrap;">
            {full_text}
        </div>
        <div style="margin-top:8px; text-align:center;">
            {icons_html}
        </div>
    </div>
    """


def sku_label_preview_html(sku: str) -> str:
    # Preview without border, and slightly bigger
    return f"""
    <div style="
        width:300px;
        height:60px;
        display:flex;
        align-items:center;
        justify-content:center;
        font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
        font-size:22px;
        letter-spacing:2px;
        margin-bottom:8px;
        ">
        {sku}
    </div>
    """


# ---------------- SIDEBAR ----------------

st.sidebar.title("Carelabel Generator")

brand = st.sidebar.selectbox("Brand", list(BRAND_LOGOS.keys()))

st.sidebar.markdown("---")
st.sidebar.caption(
    "Carelabel PDF: 80×30 mm (vertical, margens para costura, sem box).\n"
    "SKU labels PDF: 10×50 mm (horizontal, 1 SKU por página, sem box, fonte maior)."
)


# ---------------- MAIN UI ----------------

st.title("Carelabel & SKU Label Generator")

tab_care, tab_sku = st.tabs(["Carelabel (80×30 mm)", "SKU labels (10×50 mm)"])


# ---- CARELABEL TAB ----
with tab_care:
    col_left, col_right = st.columns([1.1, 1.4])

    with col_left:
        st.subheader("Carelabel – Composição")

        family_code = st.text_input(
            "Product family (para nome do arquivo)",
            value="",
            help="Ex.: C500390016 – todas as cores/SKUs desta família usam a mesma carelabel.",
        )

        st.write("### Composition")
        exterior_en = st.text_input(
            "EXTERIOR",
            value="100% PVC",
            help="English ou Português. Ex.: '75% Polyester, 25% Polyvinyl Chloride (PVC)'",
        )
        forro_en = st.text_input(
            "FORRO / LINING",
            value="100% Polyester",
            help="English ou Português. Ex.: '100% Polyester'",
        )

        already_pt = st.checkbox(
            "Composition already in Portuguese (skip auto-translation)",
            value=False,
        )

        generate_care = st.button("Generate carelabel PDF")

    with col_right:
        st.subheader("Preview & PDF")

        if generate_care:
            st.session_state["family_code"] = family_code.strip()

            if already_pt:
                exterior_pt = exterior_en.strip().upper()
                forro_pt = forro_en.strip().upper()
            else:
                exterior_pt = translate_composition_to_pt(exterior_en)
                forro_pt = translate_composition_to_pt(forro_en)

            full_text = build_carelabel_text(exterior_pt, forro_pt)

            st.markdown(
                carelabel_preview_html(full_text, brand),
                unsafe_allow_html=True,
            )

            pdf_bytes = create_carelabel_pdf(brand, full_text)
            pdf_name_base = family_code.strip() or "CARELABEL"
            st.download_button(
                "Download carelabel PDF",
                data=pdf_bytes,
                file_name=f"{pdf_name_base} - CARE LABEL.pdf",
                mime="application/pdf",
            )
        else:
            st.info("Preencha a composição e clique em **Generate carelabel PDF**.")


# ---- SKU LABELS TAB ----
with tab_sku:
    if "sku_count" not in st.session_state:
        st.session_state["sku_count"] = 4

    col_left, col_right = st.columns([1.1, 1.6])

    with col_left:
        st.subheader("SKUs para esta carelabel")

        default_family = st.session_state.get("family_code", "")
        family_code_sku = st.text_input(
            "Product family (para nome do PDF)",
            value=default_family,
            help="Ex.: C500390016 – usada apenas para nome do PDF.",
        )

        if st.button("Add another SKU field"):
            st.session_state["sku_count"] += 1

        sku_values = []
        for i in range(st.session_state["sku_count"]):
            sku_val = st.text_input(
                f"SKU {i + 1}",
                key=f"sku_{i+1}",
                placeholder="Ex.: C5003900160001",
            )
            if sku_val.strip():
                sku_values.append(sku_val.strip())

        generate_skus = st.button("Generate SKU labels PDF")

    with col_right:
        st.subheader("Preview & PDF")

        if generate_skus:
            if not sku_values:
                st.warning("Informe pelo menos um SKU.")
            else:
                for sku in sku_values:
                    st.markdown(sku_label_preview_html(sku), unsafe_allow_html=True)

                sku_pdf = create_sku_labels_pdf(sku_values)
                sku_pdf_name = family_code_sku.strip() or "SKUS"
                st.download_button(
                    "Download SKU labels PDF",
                    data=sku_pdf,
                    file_name=f"{sku_pdf_name} - SKU LABELS.pdf",
                    mime="application/pdf",
                )
        else:
            st.info("Digite os SKUs e clique em **Generate SKU labels PDF**.")
