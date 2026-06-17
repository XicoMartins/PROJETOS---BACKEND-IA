"""FORMS-MTECH - Controle de Produção
Versão refatorada sem Django, compatível com Streamlit Cloud"""

from datetime import datetime, time, date
import ast
import base64
from io import BytesIO
import os
import re
from pathlib import Path

import pandas as pd
import streamlit as st

from core.db_utils import (
    build_entry_payload_from_streamlit,
    get_db,
    is_cloud_runtime,
)
from core.excel_utils import (
    get_acabados_for_cliente,
    get_process_choices_for_acabado_e_ferramental,
    get_unique_choices,
    get_operadores,
)

st.set_page_config(
    page_title="Registro de Producao",
    page_icon="RP",
    layout="centered",
)

@st.cache_data
def load_base_choices():
    return {
        "clientes": [v for v, _ in get_unique_choices("CLIENTE") if v],
        "acabados": [v for v, _ in get_unique_choices("ACABADO") if v],
        "ferramentais": [v for v, _ in get_unique_choices("FERRAMENTAL") if v],
    }

choices = load_base_choices()
operadores = get_operadores()
SCHEMA_VERSION = "1.2"
PROCESSO_OUTRO = "__PROCESSO_OUTRO__"
BG_IMAGE_PATH = Path(__file__).resolve().parent / "assets" / "background.png"
LOGO_PATH = Path(__file__).resolve().parent / "assets" / "logo.png"

@st.cache_resource
def load_image_base64(image_path: Path) -> str | None:
    if not image_path.exists():
        return None
    return base64.b64encode(image_path.read_bytes()).decode()

def set_background(image_path: Path) -> None:
    encoded = load_image_base64(image_path)
    bg_image_layer = f'url("data:image/png;base64,{encoded}") center/cover fixed no-repeat,' if encoded else ""
    st.markdown(f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;600;700&display=swap');
        .stApp {{
            background: {bg_image_layer} linear-gradient(135deg, rgba(0,0,0,0.05), rgba(0,0,0,0.15));
            color: #0c1b1f;
            font-family: 'Manrope', 'Segoe UI', sans-serif;
        }}
        .block-container {{
            padding-top: 3rem;
            padding-bottom: 3rem;
            max-width: 980px;
        }}
        .app-hero {{
            display: flex;
            align-items: center;
            gap: 1rem;
            padding: 1rem 1.5rem;
            margin-bottom: 1.5rem;
            background: rgba(255, 255, 255, 0.82);
            border-radius: 14px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.12);
            border: 1px solid rgba(255,255,255,0.6);
            backdrop-filter: blur(4px);
        }}
        .app-hero img {{
            height: 70px;
            width: auto;
        }}
        .logo-fallback {{
            height: 70px;
            width: 70px;
            border-radius: 14px;
            background: linear-gradient(135deg, #0b4453, #0a7b8c);
            color: #fff;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 800;
            letter-spacing: 0.06em;
        }}
        .hero-text h1 {{
            font-size: 1.8rem;
            margin: 0;
            color: #0a4a52;
            letter-spacing: 0.02em;
        }}
        .hero-text p {{
            margin: 2px 0 0;
            color: #0f282f;
            font-weight: 600;
        }}
        .form-card {{
            background: rgba(255,255,255,0.9);
            border-radius: 14px;
            padding: 1.25rem;
            box-shadow: 0 10px 30px rgba(0,0,0,0.12);
            border: 1px solid rgba(10,68,83,0.12);
            backdrop-filter: blur(4px);
            color: #0a2a33;
        }}
        .form-card + .form-card {{
            margin-top: 1rem;
        }}
        .section-title {{
            font-weight: 700;
            color: #0c4a53;
            margin-bottom: 0.35rem;
        }}
        .stButton button {{
            background: linear-gradient(135deg, #0b4453, #0a7b8c);
            color: #fff;
            border: 1px solid #08333f;
            border-radius: 10px;
            padding: 0.65rem 1.05rem;
            font-weight: 700;
            letter-spacing: 0.01em;
            box-shadow: 0 10px 22px rgba(10, 68, 83, 0.35);
        }}
        .stButton button:hover {{
            filter: brightness(1.05);
            transform: translateY(-1px);
        }}
        </style>
        """, unsafe_allow_html=True)

set_background(BG_IMAGE_PATH)

def normalize_operadores(value) -> str:
    if isinstance(value, list):
        return "; ".join(str(v).strip() for v in value if str(v).strip())
    if value is None:
        return ""
    return str(value).strip()

def normalize_text(value) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    return re.sub(r"\s+", " ", text) if text else ""

def unique_preserve_order(values):
    seen = set()
    result = []
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result

def validate_inputs(cliente, acabado, numero_display, ferramental, processo, data_producao,
                   hora_iniciada, hora_finalizada, quantidade_produzida, quantidade_total,
                   numero_operadores, operadores_selecionados):
    erros = []
    obrigatorios = [(cliente, "Cliente"), (acabado, "Display"), (numero_display, "Codigo"),
                    (ferramental, "Ferramental"), (processo, "Processo"), (data_producao, "Data")]
    for valor, label in obrigatorios:
        if not valor:
            erros.append(f"{label} obrigatorio.")
    if numero_operadores < 1:
        erros.append("Numero de operadores deve ser >= 1.")
    if numero_display and not re.fullmatch(r"\d{8}", str(numero_display).strip()):
        erros.append("Codigo deve ter 8 digitos.")
    if not operadores_selecionados:
        erros.append("Selecione ao menos um operador.")
    elif len(operadores_selecionados) != numero_operadores:
        erros.append("Quantidade de operadores incorreta.")
    if hora_iniciada and hora_finalizada and hora_finalizada < hora_iniciada:
        erros.append("Hora final deve ser >= inicial.")
    if quantidade_total < quantidade_produzida:
        erros.append("Quantidade total deve ser >= produzida.")
    return erros

def salvar_registro(payload: dict):
    try:
        db = get_db()
        entry_data = build_entry_payload_from_streamlit(payload, SCHEMA_VERSION)
        entry_id = db.save_entry(entry_data)
        return entry_id, None
    except Exception as exc:
        return None, f"Erro: {str(exc)}"

def render_header():
    logo_b64 = load_image_base64(LOGO_PATH)
    logo_img = f'<img src="data:image/png;base64,{logo_b64}" />' if logo_b64 else '<div class="logo-fallback">MTECH</div>'
    st.markdown(f'''<div class="app-hero">{logo_img}<div class="hero-text"><h1>Controle Produção</h1><p>MTECH</p></div></div>''', unsafe_allow_html=True)

render_header()

db_status = get_db()
if is_cloud_runtime() and not db_status.is_persistent:
    st.warning(
        "Persistencia externa nao configurada. Configure DATABASE_URL nos Secrets "
        "do Streamlit Cloud antes de usar em producao."
    )

if "last_ferramental" not in st.session_state:
    st.session_state.last_ferramental = None
if "last_cliente" not in st.session_state:
    st.session_state.last_cliente = None
if "operadores_selecionados" not in st.session_state:
    st.session_state.operadores_selecionados = []

def reset_form_fields():
    for k in ["cliente", "acabado", "ferramental", "processo", "numero_display",
              "data_producao", "hora_iniciada", "hora_finalizada", "quantidade_produzida",
              "pecas_mortas", "quantidade_total", "numero_operadores"]:
        st.session_state.pop(k, None)

def render_lancamento_screen():
    st.markdown('<div class="form-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">Lançamento</div>', unsafe_allow_html=True)
    
    cliente = st.selectbox("Cliente", choices["clientes"], index=None, key="cliente")
    if st.session_state.last_cliente != cliente:
        st.session_state.pop("acabado", None)
    st.session_state.last_cliente = cliente
    
    acabado_options = get_acabados_for_cliente(cliente) if cliente else choices["acabados"]
    acabado = st.selectbox("Display", acabado_options, index=None, key="acabado")
    numero_display = st.text_input("Codigo (8 digitos)", key="numero_display", max_chars=8)
    ferramental = st.selectbox("Ferramental", choices["ferramentais"], index=None, key="ferramental")
    
    if st.session_state.last_ferramental != ferramental:
        st.session_state.pop("processo", None)
    st.session_state.last_ferramental = ferramental
    
    processo_options = get_process_choices_for_acabado_e_ferramental(acabado, ferramental)
    processo_options_with_outro = processo_options + [PROCESSO_OUTRO]
    processo = st.selectbox("Processo", processo_options_with_outro, index=None, key="processo",
                           format_func=lambda x: "Outro (digitar)" if x == PROCESSO_OUTRO else x)
    
    processo_custom = st.text_input("Nome do processo (novo)", key="processo_custom") if processo == PROCESSO_OUTRO else ""
    processo_selecionado = processo_custom.strip() if processo == PROCESSO_OUTRO else processo
    
    data_producao = st.date_input("Data", value=date.today(), format="DD/MM/YYYY", key="data_producao")
    hora_iniciada = st.time_input("Hora início", value=time(0,0), key="hora_iniciada")
    hora_finalizada = st.time_input("Hora fim", value=time(0,0), key="hora_finalizada")
    quantidade_produzida = st.number_input("Quantidade", min_value=0, step=1, key="quantidade_produzida")
    pecas_mortas = st.number_input("Peças mortas", min_value=0, step=1, key="pecas_mortas")
    quantidade_total = st.number_input("Quantidade total", min_value=0, step=1, key="quantidade_total")
    numero_operadores = st.number_input("Num. operadores", min_value=1, step=1, key="numero_operadores")
    
    operadores_base = unique_preserve_order([o for o in operadores if o])
    operadores_selecionados = st.multiselect(f"Operadores ({len(st.session_state.operadores_selecionados)}/{numero_operadores})",
                                             operadores_base, key="operadores_multiselect",
                                             max_selections=numero_operadores)
    st.session_state.operadores_selecionados = operadores_selecionados
    
    if st.button("Salvar"):
        erros = validate_inputs(cliente, acabado, numero_display, ferramental, processo_selecionado,
                               data_producao, hora_iniciada, hora_finalizada, quantidade_produzida,
                               quantidade_total, numero_operadores, operadores_selecionados)
        if erros:
            st.error("Erros:\n- " + "\n- ".join(erros))
        else:
            registro = {
                "cliente": cliente, "acabado": acabado, "numero_display": str(numero_display).strip(),
                "ferramental": ferramental, "processo": processo_selecionado,
                "data_producao": data_producao.strftime("%d/%m/%y"),
                "operadores": operadores_selecionados,
                "hora_iniciada": hora_iniciada.strftime("%H:%M"),
                "hora_finalizada": hora_finalizada.strftime("%H:%M"),
                "quantidade_produzida": quantidade_produzida, "pecas_mortas": pecas_mortas,
                "numero_operadores": numero_operadores, "quantidade_total": quantidade_total,
            }
            entry_id, error = salvar_registro(registro)
            if entry_id:
                st.success(f"✅ Salvo! ID #{entry_id}")
                reset_form_fields()
                st.rerun()
            else:
                st.error(error or "Erro ao salvar.")
    
    st.markdown("</div>", unsafe_allow_html=True)

def render_consulta_screen():
    st.markdown('<div class="form-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">Consultar</div>', unsafe_allow_html=True)
    
    db = get_db()
    entries = db.get_all_entries()
    
    if not entries:
        st.info("Nenhum registro.")
        st.markdown("</div>", unsafe_allow_html=True)
        return
    
    df = pd.DataFrame(entries)
    st.dataframe(df, hide_index=True, use_container_width=True)
    
    csv = df.to_csv(index=False).encode('utf-8-sig')
    st.download_button("Exportar CSV", data=csv, file_name="registros.csv", mime="text/csv")
    
    st.markdown("</div>", unsafe_allow_html=True)

tab1, tab2 = st.tabs(["📝 Lançamento", "📊 Consulta"])
with tab1:
    render_lancamento_screen()
with tab2:
    render_consulta_screen()

st.divider()
st.caption("FORMS-MTECH v1.2 - Refatorado para Streamlit Cloud")
