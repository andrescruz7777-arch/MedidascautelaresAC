# danis.py — Respuesta de medidas cautelares (Streamlit, IA only, catálogo extendido)

import streamlit as st
import pandas as pd
import io, re, os
from datetime import datetime

# ========== Extracción de texto ==========
def extract_text_pdf(file_bytes: bytes) -> str:
    """Extrae texto con PyPDF2 o pdfplumber. Si no hay texto, devuelve ''. """
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

# ========== Reglas ==========
NEG_MARKERS = [
    r"no.*titular", r"no.*presenta", r"no.*existe.*(dineros|productos|cuentas|v[ií]nculos)",
    r"no.*es.*cliente", r"sin.*v[ií]nculo", r"inexistencia.*v[ií]nculos",
    r"no.*registra.*(productos|cuentas|contratos|operaci[oó]n)",
    r"no.*posee", r"no.*hay.*(saldo|cuentas|dineros)", r"no.*lugar.*proceder",
    r"no.*ha.*sido.*posible.*aplicar.*medida", r"no.*ha.*sido.*posible.*proceder"
]
POS_MARKERS = [
    r"hemos.*atendido.*medida", r"se.*procedi[oó].*atender.*medida",
    r"se.*atend[ií]o.*medida", r"registra.*medida", r"aplicaci[oó]n.*medida",
    r"se.*aplic[oó].*medida", r"embargo.*aplicado", r"decret[oó].*embargo",
    r"fue.*debitad", r"procedimos.*atender.*medida", r"medida.*registrada"
]
INEMB_MARKERS = [r"inembargable", r"inembargables", r"art[ií]culo 594", r"ley 100 de 1993"]
SIN_SALDO_MARKERS = [
    r"sin.*saldo", r"saldo.*no.*disponible", r"no.*fue.*debitad", r"no.*fueron.*debitad",
    r"medida.*registrada.*tan pronto.*ingresen.*recursos", r"cuando.*ingresen.*recursos.*consignad"
]
PRODUCTS = [
    "cuenta de ahorros","cuentas de ahorros","cuenta corriente","cuentas corrientes",
    "cdt","cdts","cdat","cdats","fiducuenta","nequi","daviplata",
    "carteras colectivas","pensiones voluntarias","tarjeta"
]

# ========== Catálogo extendido ==========
ENTITY_DB = {
    "BANCOLOMBIA": {"domains":["bancolombia.com.co"], "names":[r"\bbancolombia\b", r"\bbanco\s+colombia\b"]},
    "BANCOLOMBIA (NEQUI)": {"domains":["nequi.co"], "names":[r"\bnequi\b"]},
    "DAVIVIENDA": {"domains":["davivienda.com"], "names":[r"\bdavivienda\b"]},
    "DAVIVIENDA (DAVIPLATA)": {"domains":["daviplata.com"], "names":[r"\bdaviplata\b"]},
    "BANCO DE BOGOTÁ": {"domains":["bancodebogota.com.co"], "names":[r"\bbanco\s+de\s+bogot[áa]\b"]},
    "BBVA": {"domains":["bbva.com.co"], "names":[r"\bbbva\b"]},
    "BANCO POPULAR": {"domains":["bancopopular.com.co"], "names":[r"\bbanco\s+popular\b"]},
    "BANCO AGRARIO": {"domains":["bancoagrario.gov.co"], "names":[r"\bbanco\s+agrario\b"]},
    "BANCO CAJA SOCIAL": {"domains":["bancocajasocial.com.co"], "names":[r"\bbanco\s+caja\s+social\b", r"\bcaja\s+social\b"]},
    "SCOTIABANK COLPATRIA": {"domains":["scotiabankcolpatria.com"], "names":[r"\bcolpatria\b", r"\bscotiabank\b"]},
    "BANCO DE OCCIDENTE": {"domains":["bancodeoccidente.com.co"], "names":[r"\bbanco\s+de\s+occidente\b"]},
    "ITAÚ": {"domains":["itau.co"], "names":[r"\bita[úu]\b", r"\bbanco\s+itau\b"]},
    "BANCO FALABELLA": {"domains":["bancofalabella.com.co"], "names":[r"\bfalabella\b"]},
    "BANCO PICHINCHA": {"domains":["pichincha.com.co"], "names":[r"\bpichincha\b"]},
    "BANCO W": {"domains":["bancow.com.co"], "names":[r"\bbanco\s+w\b"]},
    "GNB SUDAMERIS": {"domains":["gnbsudameris.com"], "names":[r"\bgnb\s*sudameris\b", r"\bsudameris\b"]},
    "SERFINANZA": {"domains":["serfinanza.com"], "names":[r"\bserfinanza\b"]},
    "BANCO MUNDO MUJER": {"domains":["mundomujer.com"], "names":[r"\bmundo\s+mujer\b"]},
    "GLOBAL 66": {"domains":["global66.com"], "names":[r"\bglobal\s*66\b"]},
    "UALÁ": {"domains":["uala.com.co"], "names":[r"\bual[áa]\b"]},
    "LULO BANK": {"domains":["lulo.bank","lulo.com.co"], "names":[r"\blulo\s*bank\b", r"\blulo\b"]},
    "MOVII": {"domains":["movii.com.co"], "names":[r"\bmovii\b"]},
    "DALE!": {"domains":["dale.com.co"], "names":[r"\bdale!?"]},
    "PROCREDIT": {"domains":["procredit.com.co"], "names":[r"\bprocredit\b"]},
    "JURISCOOP": {"domains":["juriscoop.com.co"], "names":[r"\bjuriscoop\b"]},
    "BANCOOMEVA": {"domains":["bancoomeva.com.co"], "names":[r"\bbancoomeva\b"]},
    "BANCAMÍA": {"domains":["bancamia.com.co"], "names":[r"\bbancam[ií]a\b"]},
    "BANCO AV VILLAS": {"domains":["avvillas.com.co"], "names":[r"\bav\s*villas\b"]},
    "CITIBANK COLOMBIA": {"domains":["citibank.com.co"], "names":[r"\bcitibank\b"]},
    "COOPCENTRAL": {"domains":["coopcentral.com.co"], "names":[r"\bcoopcentral\b"]},
    "BANCO SANTANDER DE NEGOCIOS": {"domains":["santander.com.co"], "names":[r"\bsantander\b"]},
    "MIBANCO": {"domains":["mibanco.com.co"], "names":[r"\bmibanco\b"]},
    "TUYA": {"domains":["tuya.com.co"], "names":[r"\btuya\b"]},
    "BOLD": {"domains":["bold.com.co"], "names":[r"\bbold\b"]},
}

def build_detectors(extra_raw: str):
    detectors=[]
    for canon,d in ENTITY_DB.items():
        regexes=[re.compile(pat,re.IGNORECASE) for pat in d.get("names",[])]
        detectors.append((canon,regexes,d.get("domains",[])))
    if extra_raw.strip():
        for line in extra_raw.splitlines():
            if "=" in line:
                name,pats=line.split("=",1)
                regexes=[re.compile(p.strip(),re.IGNORECASE) for p in pats.split("|") if p.strip()]
                detectors.append((name.strip(),regexes,[]))
    return detectors

def detect_entity(filename:str,text:str,detectors)->str:
    hay=f"{filename}\n{text}".lower()
    for canon,regexes,domains in detectors:
        if any(dom.lower() in hay for dom in domains): return canon
    for canon,regexes,domains in detectors:
        if any(rx.search(hay) for rx in regexes): return canon
    return filename.rsplit(".",1)[0].upper()

def classify(text:str)->dict:
    t=text.lower()
    positive=any(re.search(p,t) for p in POS_MARKERS)
    negative=any(re.search(n,t) for n in NEG_MARKERS)
    inembargable=any(re.search(k,t) for k in INEMB_MARKERS)
    sin_saldo=any(re.search(k,t) for k in SIN_SALDO_MARKERS)
    prods=sorted({kw for kw in PRODUCTS if kw in t})
    return {"positive":positive and not negative,"negative":negative and not positive,
            "inembargable":inembargable,"sin_saldo":sin_saldo,"products":prods}

def render_line(entity:str,cls:dict)->str:
    if cls["positive"]:
        details=[]
        if cls["sin_saldo"]: details.append("SIN SALDO DISPONIBLE / EN ESPERA DE RECURSOS")
        if cls["inembargable"]: details.append("PRODUCTO NO SUSCEPTIBLE DE EMBARGO")
        if cls["products"]: details.append("PRODUCTO(S): "+", ".join(p.upper() for p in cls["products"]))
        suf=(", "+". ".join(details)+".") if details else "."
        return f"{entity}: REGISTRA MEDIDA{suf}"
    if cls["inembargable"]: return f"{entity}: PRODUCTO NO SUSCEPTIBLE DE EMBARGO"
    if cls["negative"]: return f"{entity}: SIN VÍNCULO COMERCIAL"
    return f"{entity}: NO SE PUDO DETERMINAR (REVISIÓN MANUAL)"

# ========== IA opcional ==========
def try_ai_summarize(text:str,entity:str)->str:
    try:
        from openai import OpenAI
        api_key=os.getenv("OPENAI_API_KEY") or st.secrets.get("OPENAI_API_KEY")
        if not api_key: return f"{entity}: NO SE PUDO DETERMINAR (SIN API KEY)"
        client=OpenAI(api_key=api_key)
        prompt=f"""
Eres un asistente jurídico colombiano. Resume UNA SOLA LÍNEA:
- Si NO hay productos → "SIN VÍNCULO COMERCIAL".
- Si SÍ hay medida aplicada → "REGISTRA MEDIDA" + detalles si aplica.
- Si inembargable → "PRODUCTO NO SUSCEPTIBLE DE EMBARGO".
Devuelve exactamente: "{entity}: <TEXTO EN MAYÚSCULAS, BREVE>".
Texto: <<<{text}>>>"""
        resp=client.chat.completions.create(
            model="gpt-4o-mini",temperature=0,
            messages=[{"role":"user","content":prompt}]
        )
        return resp.choices[0].message.content.strip()
    except Exception:
        return f"{entity}: NO SE PUDO DETERMINAR (ERROR IA)"

# ========== UI ==========
st.set_page_config(page_title="⚖️ Medidas cautelares (IA)", layout="wide")
st.title("⚖️ Respuesta de medidas cautelares — COS JudicIA (Cloud)")

with st.sidebar:
    use_ai=st.toggle("Usar IA si no hay texto / ambiguo", value=True)
    extra_raw=st.text_area("Añadir instituciones (regex)", height=150)

uploaded_files=st.file_uploader("Cargar PDFs", type=["pdf"], accept_multiple_files=True)
DETECTORS=build_detectors(extra_raw)

if uploaded_files:
    rows=[]
    from PyPDF2 import PdfMerger
    pdf_merger=PdfMerger()

    for uf in uploaded_files:
        pdf_bytes=uf.read()
        text=extract_text_pdf(pdf_bytes)
        entity=detect_entity(uf.name,text,DETECTORS)
        cls=classify(text)
        line=render_line(entity,cls)
        if ("NO SE PUDO" in line) and use_ai:
            line=try_ai_summarize(text or "SIN TEXTO",entity)
        rows.append({"archivo":uf.name,"institución":entity,"resultado":line})
        try: pdf_merger.append(io.BytesIO(pdf_bytes))
        except: pass

    df=pd.DataFrame(rows)
    st.dataframe(df,use_container_width=True,hide_index=True)
    guion="\n".join(r["resultado"] for r in rows)
    st.subheader("Guion estandarizado")
    st.code(guion)
    st.download_button("⬇️ Guion (.txt)",data=guion.encode(),file_name="guion.txt")
    st.download_button("⬇️ CSV",data=df.to_csv(index=False).encode(),file_name="resumen.csv")
    out=io.BytesIO()
    pdf_merger.write(out); pdf_merger.close()
    st.download_button("⬇️ PDF unificado",data=out.getvalue(),file_name="Respuestas_Unificadas.pdf")
else:
    st.info("Sube PDFs para analizar.")
