import re
import base64
from pathlib import Path

import streamlit as st

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

BRAND_WEBSITES = {
    # adjust if needed
    "Anacapri": "ANACAPRI.COM.BR",
    "Arezzo": "AREZZO.COM.BR",
    "Schutz": "SCHUTZ.COM.BR",
    "Reserva": "RESERVA.COM.BR",
}


# ---------------- HELPERS ----------------

def load_image_base64(path: Path):
    if not path.exists():
        return None
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


BRAND_LOGOS_B64 = {name: load_image_base64(p) for name, p in BRAND_LOGOS.items()}
CARE_ICONS_B64 = load_image_base64(CARE_ICONS_PATH)


def translate_composition_to_pt(text: str) -> str:
    """
    Simple rule-based translator for handbag compositions EN -> PT-BR.
    Extend the replacements list as needed.
    """
    if not text:
        return ""

    result = text.strip()

    replacements = [
        # more specific patterns first
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
    """
    Fixed carelabel text with dynamic EXTERIOR / FORRO.
    """
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


def label_box_html(full_text: str, brand: str) -> str:
    """
    HTML that simulates the 80x30mm carelabel layout similar to your mockup:
    - Thin border
    - Logo area at top (we'll use the brand name + optional logo)
    - Body text
    - Care icons at the bottom
    """
    brand_upper = brand.upper()
    website = BRAND_WEBSITES.get(brand, f"{brand_upper}.COM.BR")

    logo_b64 = BRAND_LOGOS_B64.get(brand)
    logo_html = (
        f'<img src="data:image/png;base64,{logo_b64}" '
        f'style="max-width:140px; margin-bottom:4px;" />'
        if logo_b64
        else ""
    )

    icons_html = (
        f'<img src="data:image/png;base64,{CARE_ICONS_B64}" '
        f'style="width:100%; margin-top:10px;" />'
        if CARE_ICONS_B64
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
            <div style="
                font-size:24px;
                font-weight:700;
                letter-spacing:3px;
                margin-top:2px;">
                {brand_upper}
            </div>
            <div style="
                font-size:10px;
                font-weight:700;
                margin-top:2px;">
                {website}
            </div>
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


def sku_label_html(sku: str) -> str:
    """
    HTML that simulates the 10x50mm SKU label:
    border, SKU centered, similar to your example.
    """
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
        ">
        {sku}
    </div>
    """


# ---------------- SIDEBAR ----------------
st.sidebar.title("Carelabel Generator")

brand = st.sidebar.selectbox("Brand", list(BRAND_LOGOS.keys()))

st.sidebar.markdown("---")
st.sidebar.caption(
    "Use the Carelabel tab for the family composition and the SKU tab "
    "to list all SKUs that share this carelabel."
)


# ---------------- MAIN LAYOUT ----------------
st.title("Carelabel & SKU Label Generator")

tab_care, tab_sku = st.tabs(["Carelabel (80×30 mm)", "SKU labels (10×50 mm)"])


# ---------- CARELABEL TAB ----------
with tab_care:
    col_left, col_right = st.columns([1.1, 1.3])

    with col_left:
        st.subheader("Carelabel – Composition")

        family_code = st.text_input(
            "Product family (optional)",
            value="",
            help="e.g. C500390016 – all colors/SKUs in this family share the same carelabel.",
        )

        st.write("### Composition (English or Portuguese)")
        exterior_en = st.text_input(
            "EXTERIOR",
            value="100% PVC",
            help="Example: '75% Polyester, 25% Polyvinyl Chloride (PVC)'",
        )
        forro_en = st.text_input(
            "FORRO / LINING",
            value="100% Polyester",
            help="Example: '100% Polyester'",
        )

        already_pt = st.checkbox(
            "Composition is already in Portuguese (skip auto-translation)",
            value=False,
        )

        st.markdown("—")
        file_base_name = st.text_input(
            "Base file name (optional)",
            value=family_code or "",
            help="Used only for the .txt file name. Example: C500390016",
        )

        generate_care = st.button("Generate carelabel")

    with col_right:
        st.subheader("Carelabel Preview")

        if generate_care:
            if already_pt:
                exterior_pt = exterior_en.strip().upper()
                forro_pt = forro_en.strip().upper()
            else:
                exterior_pt = translate_composition_to_pt(exterior_en)
                forro_pt = translate_composition_to_pt(forro_en)

            full_text = build_carelabel_text(exterior_pt, forro_pt)

            st.markdown(
                label_box_html(full_text, brand),
                unsafe_allow_html=True,
            )

            # download text
            base_name = file_base_name.strip() or "carelabel"
            st.download_button(
                "Download carelabel text (.txt)",
                data=full_text,
                file_name=f"{base_name}_carelabel.txt",
                mime="text/plain",
            )
        else:
            st.info("Preencha a composição e clique em **Generate carelabel**.")


# ---------- SKU LABELS TAB ----------
with tab_sku:
    if "sku_count" not in st.session_state:
        st.session_state["sku_count"] = 4  # start with 4 SKUs

    col_left, col_right = st.columns([1.1, 1.5])

    with col_left:
        st.subheader("SKUs for this family")

        st.caption(
            "Exemplo: família **C500390016** com 4 cores → "
            "C5003900160001, C5003900160002, C5003900160003, C5003900160004."
        )

        # optional hint from family code typed on carelabel tab
        if family_code := st.session_state.get("family_code", ""):
            st.write(f"Família atual (opcional): **{family_code}**")

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

        generate_skus = st.button("Generate SKU labels")

    with col_right:
        st.subheader("SKU Label Previews")

        if generate_skus and sku_values:
            for sku in sku_values:
                st.markdown(sku_label_html(sku), unsafe_allow_html=True)
                st.write("")

            # text file with one SKU per line (useful for ZPL / printing later)
            skus_text = "\n".join(sku_values)
            st.download_button(
                "Download SKU list (.txt)",
                data=skus_text,
                file_name="sku_list.txt",
                mime="text/plain",
            )
        else:
            st.info(
                "Digite os SKUs (pelo menos um) e clique em **Generate SKU labels** "
                "para visualizar as etiquetas."
            )
