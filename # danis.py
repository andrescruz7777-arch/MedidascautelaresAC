# danis.py — Respuesta de medidas cautelares (Streamlit + OCR + IA opcional)
# Incluye catálogo extendido de bancos y billeteras de Colombia

import streamlit as st
import pandas as pd
import io, re, os
from datetime import datetime

# ========== Extracción de texto ==========
def extract_text_pdf(file_bytes: bytes) -> str:
    text = ""
    try:
        from PyPDF2 import PdfReader
        reader = PdfReader(io.BytesIO(file_bytes))
        parts = [p.extract_text() or "" for p in reader.pages]
        text = "\n".join(parts)
    except Exception:
        text = ""
    if not text.strip():
        try:
            import pdfplumber
            with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
                parts = [pg.extract_text() or "" for pg in pdf.pages]
                text = "\n".join(parts)
        except Exception:
            text = ""
    return text or ""

def ocr_if_needed(file_bytes: bytes, lang_hint: str = "spa") -> str:
    try:
        from pdf2image import convert_from_bytes
        import pytesseract
    except Exception:
        return ""
    try:
        images = convert_from_bytes(file_bytes, dpi=300)
    except Exception:
        return ""
    texts = []
    for img in images:
        try:
            texts.append(pytesseract.image_to_string(img, lang=lang_hint) or "")
        except Exception:
            texts.append("")
    return "\n".join(texts).strip()

# ========== Reglas ==========
NEG_MARKERS = [
    "no es titular","no son titulares","no presenta","no presentan","no existen dineros",
    "no existen productos","no tienen celebrados contratos","no es cliente","no son clientes",
    "sin vínculo","sin vinculo","inexistencia de vínculos","no registra productos","no registran productos",
    "no registra cuentas","no hay dineros","no hay lugar para proceder","no posee productos","no posee cuentas","no posee",
    "no registra ninguna operación pasiva","no posee productos de depósito","no posee vínculo","no posee vínculos",
    "no hay cuentas","no hay saldo",
    # 👇 nuevo patrón que detecta esta frase
    "no ha sido posible proceder con la aplicación de la medida",]
POS_MARKERS = [
    "hemos.*atendido.*medida",
    "se.*procedi[oó].*atender.*medida",
    "se.*atend[ií]o.*medida",
    "registra.*medida",
    "aplicaci[oó]n.*medida",
    "se.*aplic[oó].*medida",
    "embargo.*aplicado",
    "decret[oó].*embargo",
    "fue.*debitad",
    "procedimos.*atender.*medida",
    "medida.*registrada",    # más general
]

INEMB_MARKERS = ["inembargable","inembargables","artículo 594","articulo 594","art. 134","ley 100 de 1993"]
SIN_SALDO_MARKERS = [
    "sin.*saldo",
    "saldo.*no.*disponible",
    "no.*fue.*debitado",
    "no.*fueron.*debitados",
    "la medida se encuentra registrada.*tan pronto.*ingresen.*recursos",
    "cuando.*ingresen.*recursos.*serán.*consignados",
]

PRODUCTS = ["cuenta de ahorros","cuentas de ahorros","cuenta corriente","cuentas corrientes","cdt","cdts","cdat","cdats",
    "fiducuenta","nequi","daviplata","carteras colectivas","pensiones voluntarias","tarjeta"]

# ========== Catálogo extendido ==========
ENTITY_DB = {
    "BANCOLOMBIA": {
        "domains": ["bancolombia.com.co"],
        "names": [r"\bbancolombia\b", r"\bbanco\s+colombia\b"],
    },
    "BANCOLOMBIA (NEQUI)": {
        "domains": ["nequi.co"],
        "names": [r"\bnequi\b"],
    },
    "BANCO DE BOGOTÁ": {
        "domains": ["bancodebogota.com.co"],
        "names": [r"\bbanco\s+de\s+bogot[áa]\b"],
    },
    "DAVIVIENDA": {
        "domains": ["davivienda.com"],
        "names": [r"\bdavivienda\b"],
    },
    "DAVIVIENDA (DAVIPLATA)": {
        "domains": ["daviplata.com"],
        "names": [r"\bdaviplata\b"],
    },
    "BBVA": {
        "domains": ["bbva.com.co"],
        "names": [r"\bbbva\b"],
    },
    "BANCO POPULAR": {
        "domains": ["bancopopular.com.co"],
        "names": [r"\bbanco\s+popular\b"],
    },
    "BANCO AGRARIO": {
        "domains": ["bancoagrario.gov.co"],
        "names": [r"\bbanco\s+agrario\b"],
    },
    "BANCO CAJA SOCIAL": {
        "domains": ["bancocajasocial.com.co"],
        "names": [r"\bbanco\s+caja\s+social\b", r"\bcaja\s+social\b"],
    },
    "SCOTIABANK COLPATRIA": {
        "domains": ["scotiabankcolpatria.com"],
        "names": [r"\bcolpatria\b", r"\bscotiabank\b"],
    },
    "BANCO DE OCCIDENTE": {
        "domains": ["bancodeoccidente.com.co"],
        "names": [r"\bbanco\s+de\s+occidente\b"],
    },
    "ITAÚ": {
        "domains": ["itau.co"],
        "names": [r"\bita[úu]\b", r"\bbanco\s+itau\b"],
    },
    "BANCO FALABELLA": {
        "domains": ["bancofalabella.com.co"],
        "names": [r"\bfalabella\b"],
    },
    "BANCO PICHINCHA": {
        "domains": ["pichincha.com.co"],
        "names": [r"\bpichincha\b"],
    },
    "BANCO W": {
        "domains": ["bancow.com.co"],
        "names": [r"\bbanco\s+w\b"],
    },
    "GNB SUDAMERIS": {
        "domains": ["gnbsudameris.com"],
        "names": [r"\bgnb\s*sudameris\b", r"\bsudameris\b"],
    },
    "SERFINANZA": {
        "domains": ["serfinanza.com"],
        "names": [r"\bserfinanza\b"],
    },
    "BANCO MUNDO MUJER": {
        "domains": ["mundomujer.com"],
        "names": [r"\bmundo\s+mujer\b"],
    },
    "GLOBAL 66": {
        "domains": ["global66.com"],
        "names": [r"\bglobal\s*66\b"],
    },
    "UALÁ": {
        "domains": ["uala.com.co"],
        "names": [r"\bual[áa]\b"],
    },
    "LULO BANK": {
        "domains": ["lulo.bank","lulo.com.co"],
        "names": [r"\blulo\s*bank\b", r"\blulo\b"],
    },
    "MOVII": {
        "domains": ["movii.com.co"],
        "names": [r"\bmovii\b"],
    },
    "DALE!": {
        "domains": ["dale.com.co"],
        "names": [r"\bdale!\b", r"\bdale\b"],
    },
    "PROCREDIT": {
        "domains": ["procredit.com.co"],
        "names": [r"\bprocredit\b"],
    },
    "JURISCOOP": {
        "domains": ["juriscoop.com.co"],
        "names": [r"\bjuriscoop\b"],
    },
    "BANCOOMEVA": {
        "domains": ["bancoomeva.com.co"],
        "names": [r"\bbancoomeva\b"],
    },
    "BANCAMÍA": {
        "domains": ["bancamia.com.co"],
        "names": [r"\bbancam[ií]a\b"],
    },
    "BANCO AV VILLAS": {
        "domains": ["avvillas.com.co"],
        "names": [r"\bav\s*villas\b"],
    },
    "CITIBANK COLOMBIA": {
        "domains": ["citibank.com.co"],
        "names": [r"\bcitibank\b"],
    },
    "COOPCENTRAL": {
        "domains": ["coopcentral.com.co"],
        "names": [r"\bcoopcentral\b"],
    },
    "BANCO SANTANDER DE NEGOCIOS": {
        "domains": ["santander.com.co"],
        "names": [r"\bsantander\b"],
    },
    "MIBANCO": {
        "domains": ["mibanco.com.co"],
        "names": [r"\bmibanco\b"],
    },
    "TUYA": {
        "domains": ["tuya.com.co"],
        "names": [r"\btuya\b"],
    },
    "BOLD": {
        "domains": ["bold.com.co"],
        "names": [r"\bbold\b"],
    },
}

def build_detectors(extra_raw: str):
    detectors = []
    for canon, d in ENTITY_DB.items():
        name_regexes = [re.compile(pat, re.IGNORECASE) for pat in d.get("names", [])]
        domains = d.get("domains", [])
        detectors.append((canon, name_regexes, domains))
    if extra_raw.strip():
        for line in extra_raw.splitlines():
            if "=" in line:
                name, pats = line.split("=", 1)
                pats_list = [p.strip() for p in pats.split("|") if p.strip()]
                if name and pats_list:
                    regexes = [re.compile(p, re.IGNORECASE) for p in pats_list]
                    detectors.append((name.strip(), regexes, []))
    return detectors

def detect_entity(filename: str, text: str, detectors) -> str:
    hay = f"{filename}\n{text}".lower()
    for canon, regexes, domains in detectors:
        for dom in domains:
            if dom.lower() in hay:
                return canon
    for canon, regexes, domains in detectors:
        for rx in regexes:
            if rx.search(hay):
                return canon
    return filename.rsplit(".",1)[0].upper()

def classify(text: str) -> dict:
    t = (text or "").lower()
    positive = any(p in t for p in POS_MARKERS) or ("registra medida" in t)
    negative = any(n in t for n in NEG_MARKERS)
    inembargable = any(k in t for k in INEMB_MARKERS)
    sin_saldo = any(k in t for k in SIN_SALDO_MARKERS)
    prods = sorted({kw for kw in PRODUCTS if kw in t})
    return {"positive": positive and not negative,"negative": negative and not positive,
            "inembargable": inembargable,"sin_saldo": sin_saldo,"products": prods}

def render_line(entity: str, cls: dict) -> str:
    if cls["positive"]:
        details=[]
        if cls["sin_saldo"]: details.append("SIN SALDO DISPONIBLE. NO FUE DEBITADO VALOR ALGUNO")
        if cls["inembargable"]: details.append("PRODUCTO NO SUSCEPTIBLE DE EMBARGO")
        if cls["products"]: details.append("PRODUCTO(S): "+", ".join(p.upper() for p in cls["products"]))
        suf = (", "+". ".join(details)+".") if details else "."
        return f"{entity}: REGISTRA MEDIDA{suf}"
    if cls["inembargable"]: return f"{entity}: PRODUCTO NO SUSCEPTIBLE DE EMBARGO"
    if cls["negative"]: return f"{entity}: SIN VÍNCULO COMERCIAL"
    return f"{entity}: NO SE PUDO DETERMINAR (REVISIÓN MANUAL)"

# ========== IA opcional ==========
def try_ai_summarize(text: str, entity: str) -> str:
    if not text.strip():
        return f"{entity}: NO SE PUDO DETERMINAR (REVISIÓN MANUAL)"
    try:
        import os
        from openai import OpenAI
        api_key = os.getenv("OPENAI_API_KEY") or st.secrets.get("OPENAI_API_KEY")
        if not api_key: return f"{entity}: NO SE PUDO DETERMINAR (REVISIÓN MANUAL)"
        client = OpenAI(api_key=api_key)
        prompt = f"""
Eres un asistente jurídico colombiano. Resume UNA SOLA LÍNEA estandarizada:
- Si NO hay productos → "SIN VÍNCULO COMERCIAL".
- Si SÍ hay medida → "REGISTRA MEDIDA" + detalles.
- Si inembargable → "PRODUCTO NO SUSCEPTIBLE DE EMBARGO".
Devuelve exactamente: "{entity}: <TEXTO MAYÚSCULAS>"
Texto: <<<{text}>>>"""
        resp = client.chat.completions.create(model="gpt-4o-mini",temperature=0,
            messages=[{"role":"user","content":prompt}])
        line = resp.choices[0].message.content.strip()
        return entity+": "+line.split(":",1)[-1].strip().upper()
    except Exception:
        return f"{entity}: NO SE PUDO DETERMINAR (REVISIÓN MANUAL)"

# ========== UI ==========
st.set_page_config(page_title="⚖️ Medidas cautelares", layout="wide")
st.title("⚖️ Respuesta de medidas cautelares — COS JudicIA")

with st.sidebar:
    use_ocr = st.toggle("Usar OCR si no hay texto", value=True)
    use_ai = st.toggle("Usar IA si sigue ambiguo", value=False)
    extra_raw = st.text_area("Añadir instituciones (regex)", height=150)

uploaded_files = st.file_uploader("Cargar PDFs", type=["pdf"], accept_multiple_files=True)
DETECTORS = build_detectors(extra_raw)

if uploaded_files:
    rows=[]
    try:
        from PyPDF2 import PdfMerger
        pdf_merger = PdfMerger()
    except: pdf_merger=None

    for uf in uploaded_files:
        pdf_bytes=uf.read()
        text=extract_text_pdf(pdf_bytes)
        if not text.strip() and use_ocr: text=ocr_if_needed(pdf_bytes)
        entity=detect_entity(uf.name,text,DETECTORS)
        cls=classify(text)
        line=render_line(entity,cls)
        if "NO SE PUDO" in line and use_ai: line=try_ai_summarize(text,entity)
        rows.append({"archivo":uf.name,"institución":entity,"resultado":line})
        if pdf_merger: 
            try: pdf_merger.append(io.BytesIO(pdf_bytes))
            except: pass

    df=pd.DataFrame(rows)
    st.dataframe(df,use_container_width=True,hide_index=True)
    guion="\n".join(r["resultado"] for r in rows)
    st.subheader("Guion")
    st.code(guion)
    st.download_button("⬇️ Guion (.txt)",data=guion.encode(),file_name="guion.txt")
    st.download_button("⬇️ CSV",data=df.to_csv(index=False).encode(),file_name="resumen.csv")
    if pdf_merger:
        out=io.BytesIO()
        try:
            pdf_merger.write(out); pdf_merger.close()
            st.download_button("⬇️ PDF unificado",data=out.getvalue(),file_name="Respuestas_Unificadas.pdf")
        except: st.warning("No se pudo unificar algunos PDFs.")
else:
    st.info("Sube PDFs para analizar.")
