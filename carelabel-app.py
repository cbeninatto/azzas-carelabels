import re
from pathlib import Path

import streamlit as st

# ---------- BASIC CONFIG ----------
st.set_page_config(
    page_title="Carelabel Generator",
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


# ---------- TRANSLATION LOGIC ----------

def translate_composition_to_pt(text: str) -> str:
    """
    Very simple rule-based translator for handbag compositions.
    You can extend this dictionary as needed.
    """
    if not text:
        return ""

    result = text.strip()

    replacements = [
        # order matters: more specific patterns first
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

    # final style: uppercase everything (numbers/percentages stay the same)
    return result.upper()


def build_carelabel_text(exterior_pt: str, forro_pt: str) -> str:
    """
    Returns the full Portuguese text block for the carelabel.
    Only EXTERIOR and FORRO are dynamic.
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


def label_box_html(inner_text: str) -> str:
    """
    Simple HTML/CSS block that simulates an 80x30mm label in preview.
    """
    return f"""
    <div style="
        border:1px solid #000;
        padding:6px 10px;
        width:380px;
        min-height:140px;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        font-size:11px;
        line-height:1.3;
        white-space:pre-wrap;
        ">
        {inner_text}
    </div>
    """


def sku_label_html(sku: str) -> str:
    """
    Simple HTML/CSS block that simulates a 10x50mm SKU label with centered SKU.
    """
    return f"""
    <div style="
        border:1px solid #000;
        width:300px;
        height:60px;
        display:flex;
        align-items:center;
        justify-content:center;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        font-size:18px;
        font-weight:600;
        letter-spacing:2px;
        ">
        {sku}
    </div>
    """


# ---------- SIDEBAR: GLOBAL OPTIONS ----------
st.sidebar.title("Carelabel Generator")

brand = st.sidebar.selectbox("Brand", list(BRAND_LOGOS.keys()))
label_type = st.sidebar.radio(
    "Label type",
    ["Carelabel (80x30mm)", "SKU label (10x50mm)"],
)

st.sidebar.markdown("---")
st.sidebar.caption("This is an internal tool draft. Update the mapping in `translate_composition_to_pt()` as needed.")


# ---------- MAIN LAYOUT ----------
st.title("Carelabel & SKU Label Generator")

col_inputs, col_preview = st.columns([1.1, 1.3])

# ---------- CARELABEL TAB ----------
if label_type.startswith("Carelabel"):
    with col_inputs:
        st.subheader("Carelabel – Input")

        st.write("### Composition (English)")
        st.write("Only *EXTERIOR* and *FORRO* will be translated and injected into the label.")

        exterior_en = st.text_input(
            "EXTERIOR (English composition)",
            value="100% PVC",
            help="Example: '60% PVC 40% Polyester'",
        )

        forro_en = st.text_input(
            "FORRO / LINING (English composition)",
            value="100% Polyester",
            help="Example: '100% Polyester'",
        )

        already_pt = st.checkbox(
            "Composition is already in Portuguese (skip auto-translation)",
            value=False,
        )

        sku_optional = st.text_input(
            "Optional SKU (used for file name only)",
            value="",
        )

        generate = st.button("Generate carelabel")

    with col_preview:
        st.subheader("Preview")

        # logo preview
        logo_path = BRAND_LOGOS.get(brand)
        if logo_path and logo_path.exists():
            st.image(str(logo_path), caption=f"Logo – {brand}", use_column_width=False)
        else:
            st.warning(f"Logo file not found for brand '{brand}'. Check assets folder.")

        if generate:
            if already_pt:
                exterior_pt = exterior_en.strip().upper()
                forro_pt = forro_en.strip().upper()
            else:
                exterior_pt = translate_composition_to_pt(exterior_en)
                forro_pt = translate_composition_to_pt(forro_en)

            full_text = build_carelabel_text(exterior_pt, forro_pt)

            # label box
            st.markdown(label_box_html(full_text), unsafe_allow_html=True)

            # care icons
            if CARE_ICONS_PATH.exists():
                st.image(str(CARE_ICONS_PATH), use_column_width=True, caption="Wash instruction icons")
            else:
                st.warning("Carelabel icons image not found. Add it to assets as 'carelabel_icons.png'.")

            # download text
            filename_sku = sku_optional.strip().replace(" ", "_") or "carelabel"
            st.download_button(
                label="Download label text (.txt)",
                data=full_text,
                file_name=f"{filename_sku}_carelabel.txt",
                mime="text/plain",
            )
        else:
            st.info("Fill the compositions and click **Generate carelabel** to see the preview.")


# ---------- SKU LABEL TAB ----------
else:
    with col_inputs:
        st.subheader("SKU label – Input")

        sku_code = st.text_input(
            "SKU (central text on label)",
            value="C40008 0001 0001",
        )

        st.caption("For this project the SKU label is 10x50mm with only the SKU centered.")

        generate_sku = st.button("Generate SKU label")

    with col_preview:
        st.subheader("Preview")

        logo_path = BRAND_LOGOS.get(brand)
        if logo_path and logo_path.exists():
            st.image(str(logo_path), caption=f"Logo – {brand}", use_column_width=False)
        else:
            st.warning(f"Logo file not found for brand '{brand}'. Check assets folder.")

        if generate_sku:
            st.markdown(sku_label_html(sku_code), unsafe_allow_html=True)

            st.download_button(
                label="Download SKU text (.txt)",
                data=sku_code.strip(),
                file_name=f"sku_label_{sku_code.strip().replace(' ', '_')}.txt",
                mime="text/plain",
            )
        else:
            st.info("Type the SKU and click **Generate SKU label** to see the preview.")
