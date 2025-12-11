import re
from io import BytesIO
from pathlib import Path
import base64

import streamlit as st

from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader


# ------------- BASIC CONFIG -------------

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


def load_image_base64(path: Path):
    if not path.exists():
        return None
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


BRAND_LOGOS_B64 = {name: load_image_base64(p) for name, p in BRAND_LOGOS.items()}
CARE_ICONS_B64 = load_image_base64(CARE_ICONS_PATH)


# ------------- TRANSLATION LOGIC -------------

def translate_composition_to_pt(text: str) -> str:
    """Very simple EN -> PT-BR translator for compositions."""
    if not text:
        return ""

    result = text.strip()

    replacements = [
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

    for pattern, repl in replacements:
        result = re.sub(pattern, repl, result, flags=re.IGNORECASE)

    return result.upper()


def build_carelabel_text(exterior_pt: str, forro_pt: str) -> str:
    """Fixed Portuguese body with dynamic EXTERIOR / FORRO."""
    text = f"""IMPORTADO POR BTG PACTUAL
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
    return text


# ------------- PDF GENERATION -------------

def create_carelabel_pdf(brand: str, full_text: str) -> bytes:
    """
    Creates a single-page PDF with page size 30x80 mm (W x H),
    border, logo at top, text and care icons at bottom.
    """
    width = 30 * mm
    height = 80 * mm

    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=(width, height))

    # Border
    c.setLineWidth(0.5)
    c.rect(0.5 * mm, 0.5 * mm, width - 1 * mm, height - 1 * mm)

    margin_x = 3 * mm

    # Logo (only image, no extra text)
    logo_path = BRAND_LOGOS.get(brand)
    if logo_path and logo_path.exists():
        logo_img = ImageReader(str(logo_path))
        logo_w, logo_h = logo_img.getSize()
        max_logo_w = width - 2 * margin_x
        max_logo_h = 15 * mm
        scale = min(max_logo_w / logo_w, max_logo_h / logo_h)
        draw_w = logo_w * scale
        draw_h = logo_h * scale
        x_logo = (width - draw_w) / 2.0
        y_logo = height - 3 * mm - draw_h
        c.drawImage(
            logo_img,
            x_logo,
            y_logo,
            width=draw_w,
            height=draw_h,
            preserveAspectRatio=True,
            mask="auto",
        )
        text_top_y = y_logo - 2 * mm
    else:
        text_top_y = height - 8 * mm  # fallback

    # Care icons at bottom
    icons_bottom_y = 3 * mm
    text_bottom_limit = icons_bottom_y
    if CARE_ICONS_PATH.exists():
        icons_img = ImageReader(str(CARE_ICONS_PATH))
        icons_w, icons_h = icons_img.getSize()
        max_icons_w = width - 2 * margin_x
        max_icons_h = 10 * mm
        scale_i = min(max_icons_w / icons_w, max_icons_h / icons_h)
        draw_w_i = icons_w * scale_i
        draw_h_i = icons_h * scale_i
        x_icons = (width - draw_w_i) / 2.0
        y_icons = icons_bottom_y
        c.drawImage(
            icons_img,
            x_icons,
            y_icons,
            width=draw_w_i,
            height=draw_h_i,
            preserveAspectRatio=True,
            mask="auto",
        )
        text_bottom_limit = y_icons + draw_h_i + 1.5 * mm

    # Body text
    text_obj = c.beginText()
    text_obj.setFont("Helvetica", 6.5)
    text_obj.setTextOrigin(margin_x, text_top_y)

    for line in full_text.splitlines():
        # stop if we are too low (basic overflow protection)
        if text_obj.getY() <= text_bottom_limit:
            break
        text_obj.textLine(line)

    c.drawText(text_obj)

    c.showPage()
    c.save()
    pdf_bytes = buf.getvalue()
    buf.close()
    return pdf_bytes


def create_sku_labels_pdf(skus: list[str]) -> bytes:
    """
    Creates a multi-page PDF.
    Each page = 50x10 mm, border, SKU centered.
    """
    width = 50 * mm
    height = 10 * mm

    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=(width, height))

    for sku in skus:
        sku = sku.strip()
        if not sku:
            continue

        c.setLineWidth(0.5)
        c.rect(0.5 * mm, 0.5 * mm, width - 1 * mm, height - 1 * mm)

        c.setFont("Helvetica", 10)
        c.drawCentredString(width / 2.0, height / 2.0 - 3, sku)

        c.showPage()

    c.save()
    pdf_bytes = buf.getvalue()
    buf.close()
    return pdf_bytes


# ------------- HTML PREVIEW (for UI only) -------------

def carelabel_preview_html(full_text: str, brand: str) -> str:
    """Tall carelabel preview with logo image and icons (HTML only)."""
    logo_b64 = BRAND_LOGOS_B64.get(brand)
    icons_b64 = CARE_ICONS_B64

    logo_html = (
        f'<img src="data:image/png;base64,{logo_b64}" '
        f'style="max-width:140px; margin-bottom:6px;" />'
        if logo_b64
        else ""
    )

    icons_html = (
        f'<img src="data:image/png;base64,{icons_b64}" '
        f'style="width:100%; margin-top:10px;" />'
        if icons_b64
        else ""
    )

    return f"""
    <div style="
        border:1px solid #000;
        padding:8px 10px;
        width:260px;
        min-height:520px;
        font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
        ">
        <div style="text-align:center; margin-bottom:10px;">
            {logo_html}
        </div>
        <div style="
            font-size:9px;
            line-height:1.35;
            white-space:pre-wrap;
            ">
            {full_text}
        </div>
        <div style="margin-top:8px; text-align:center;">
            {icons_html}
        </div>
    </div>
    """


def sku_label_preview_html(sku: str) -> str:
    """Simple bordered horizontal SKU preview."""
    return f"""
    <div style="
        border:1px solid #000;
        width:300px;
        height:60px;
        display:flex;
        align-items:center;
        justify-content:center;
        font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
        font-size:20px;
        letter-spacing:2px;
        margin-bottom:8px;
        ">
        {sku}
    </div>
    """


# ------------- SIDEBAR -------------

st.sidebar.title("Carelabel Generator")
brand = st.sidebar.selectbox("Brand", list(BRAND_LOGOS.keys()))

st.sidebar.markdown("---")
st.sidebar.caption(
    "Carelabel PDF: 80×30 mm (vertical).\n"
    "SKU labels PDF: 10×50 mm (one page per SKU)."
)


# ------------- MAIN UI -------------

st.title("Carelabel & SKU Label Generator")

tab_care, tab_sku = st.tabs(["Carelabel (80×30 mm)", "SKU labels (10×50 mm)"])


# ---- CARELABEL TAB ----
with tab_care:
    col_left, col_right = st.columns([1.1, 1.4])

    with col_left:
        st.subheader("Carelabel – Composition")

        family_code = st.text_input(
            "Product family (optional, for file name)",
            value="",
            help="Ex.: C500390016 – todas as cores/ SKUs desta família usam a mesma carelabel.",
        )

        st.write("### Composition")
        exterior_en = st.text_input(
            "EXTERIOR",
            value="100% PVC",
            help="English or Portuguese. Ex.: '75% Polyester, 25% Polyvinyl Chloride (PVC)'",
        )
        forro_en = st.text_input(
            "FORRO / LINING",
            value="100% Polyester",
            help="English or Portuguese. Ex.: '100% Polyester'",
        )

        already_pt = st.checkbox(
            "Composition already in Portuguese (skip auto-translation)",
            value=False,
        )

        generate_care = st.button("Generate carelabel PDF")

    with col_right:
        st.subheader("Preview & PDF")

        if generate_care:
            if already_pt:
                exterior_pt = exterior_en.strip().upper()
                forro_pt = forro_en.strip().upper()
            else:
                exterior_pt = translate_composition_to_pt(exterior_en)
                forro_pt = translate_composition_to_pt(forro_en)

            full_text = build_carelabel_text(exterior_pt, forro_pt)

            # HTML preview
            st.markdown(
                carelabel_preview_html(full_text, brand),
                unsafe_allow_html=True,
            )

            # PDF
            pdf_bytes = create_carelabel_pdf(brand, full_text)
            pdf_name_base = family_code.strip() or "CARELABEL"
            st.download_button(
                "Download carelabel PDF",
                data=pdf_bytes,
                file_name=f"CARE LABEL - {pdf_name_base}.pdf",
                mime="application/pdf",
            )
        else:
            st.info("Preencha a composição e clique em **Generate carelabel PDF**.")


# ---- SKU LABELS TAB ----
with tab_sku:
    if "sku_count" not in st.session_state:
        st.session_state["sku_count"] = 4  # start with 4 fields

    col_left, col_right = st.columns([1.1, 1.6])

    with col_left:
        st.subheader("SKUs for this carelabel")

        family_code_sku = st.text_input(
            "Product family (optional, for file name)",
            value="",
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
                # HTML previews
                for sku in sku_values:
                    st.markdown(sku_label_preview_html(sku), unsafe_allow_html=True)

                # PDF
                sku_pdf = create_sku_labels_pdf(sku_values)
                sku_pdf_name = family_code_sku.strip() or "SKUS"
                st.download_button(
                    "Download SKU labels PDF",
                    data=sku_pdf,
                    file_name=f"SKU LABELS - {sku_pdf_name}.pdf",
                    mime="application/pdf",
                )
        else:
            st.info(
                "Digite os SKUs (vários, se quiser) e clique em "
                "**Generate SKU labels PDF**."
            )
