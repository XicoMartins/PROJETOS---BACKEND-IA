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
    build_entry_update_payload_from_streamlit,
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
SAVE_SUCCESS_MESSAGE_KEY = "save_success_message"
ADJUST_SUCCESS_MESSAGE_KEY = "adjust_success_message"
RESET_FORM_REQUESTED_KEY = "reset_form_requested"
FORM_VERSION_KEY = "form_version"
FORM_FIELD_PREFIX = "form_field__"
ADJUST_FIELD_PREFIX = "adjust_field__"
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

def add_current_option(options, current_value):
    current_value = normalize_text(current_value)
    normalized_options = [normalize_text(option) for option in options if normalize_text(option)]
    if current_value and current_value not in normalized_options:
        normalized_options.insert(0, current_value)
    return unique_preserve_order(normalized_options)

def option_index(options, current_value):
    current_value = normalize_text(current_value)
    if current_value in options:
        return options.index(current_value)
    return None

def parse_date_value(value):
    if isinstance(value, date):
        return value
    text = normalize_text(value)
    for fmt in ("%d/%m/%y", "%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return date.today()

def parse_time_value(value):
    if isinstance(value, time):
        return value
    text = normalize_text(value)
    for fmt in ("%H:%M", "%H:%M:%S"):
        try:
            return datetime.strptime(text, fmt).time()
        except ValueError:
            continue
    return time(0, 0)

def split_operadores(value):
    if isinstance(value, list):
        return [normalize_text(item) for item in value if normalize_text(item)]
    text = normalize_text(value)
    if not text:
        return []
    return [part.strip() for part in text.split(";") if part.strip()]

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

try:
    db_status = get_db()
except Exception as exc:
    st.error(
        "Nao foi possivel conectar ao banco de dados persistente. "
        "Confira a DATABASE_URL nos Secrets do Streamlit Cloud e verifique se "
        "usuario, senha, host, porta, nome do banco e SSL estao corretos."
    )
    st.info(
        "Para Supabase, prefira a connection string do Transaction Pooler "
        "com `sslmode=require`. Para Neon, use a URL PostgreSQL com SSL."
    )
    st.caption(f"Detalhe tecnico: {type(exc).__name__}: {exc}")
    st.stop()
else:
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
if FORM_VERSION_KEY not in st.session_state:
    st.session_state[FORM_VERSION_KEY] = 0

def reset_form_fields():
    legacy_keys = ["cliente", "acabado", "ferramental", "processo", "processo_custom", "numero_display",
              "data_producao", "hora_iniciada", "hora_finalizada", "quantidade_produzida",
              "pecas_mortas", "quantidade_total", "numero_operadores", "operadores_multiselect"]
    for k in legacy_keys:
        st.session_state.pop(k, None)
    for k in list(st.session_state.keys()):
        if isinstance(k, str) and k.startswith(FORM_FIELD_PREFIX):
            st.session_state.pop(k, None)
    st.session_state[FORM_VERSION_KEY] += 1
    st.session_state.last_cliente = None
    st.session_state.last_ferramental = None
    st.session_state.operadores_selecionados = []

def form_key(name: str) -> str:
    return f"{FORM_FIELD_PREFIX}{st.session_state[FORM_VERSION_KEY]}__{name}"

def render_lancamento_screen():
    if st.session_state.pop(RESET_FORM_REQUESTED_KEY, False):
        reset_form_fields()

    st.markdown('<div class="form-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">Lançamento</div>', unsafe_allow_html=True)

    success_message = st.session_state.pop(SAVE_SUCCESS_MESSAGE_KEY, None)

    cliente_key = form_key("cliente")
    acabado_key = form_key("acabado")
    numero_display_key = form_key("numero_display")
    ferramental_key = form_key("ferramental")
    processo_key = form_key("processo")
    processo_custom_key = form_key("processo_custom")
    data_producao_key = form_key("data_producao")
    hora_iniciada_key = form_key("hora_iniciada")
    hora_finalizada_key = form_key("hora_finalizada")
    quantidade_produzida_key = form_key("quantidade_produzida")
    pecas_mortas_key = form_key("pecas_mortas")
    quantidade_total_key = form_key("quantidade_total")
    numero_operadores_key = form_key("numero_operadores")
    operadores_multiselect_key = form_key("operadores_multiselect")

    cliente = st.selectbox("Cliente", choices["clientes"], index=None, key=cliente_key)
    if st.session_state.last_cliente != cliente:
        st.session_state.pop(acabado_key, None)
    st.session_state.last_cliente = cliente
    
    acabado_options = get_acabados_for_cliente(cliente) if cliente else choices["acabados"]
    acabado = st.selectbox("Display", acabado_options, index=None, key=acabado_key)
    numero_display = st.text_input("Codigo (8 digitos)", key=numero_display_key, max_chars=8)
    ferramental = st.selectbox("Ferramental", choices["ferramentais"], index=None, key=ferramental_key)
    
    if st.session_state.last_ferramental != ferramental:
        st.session_state.pop(processo_key, None)
    st.session_state.last_ferramental = ferramental
    
    processo_options = get_process_choices_for_acabado_e_ferramental(acabado, ferramental)
    processo_options_with_outro = processo_options + [PROCESSO_OUTRO]
    processo = st.selectbox("Processo", processo_options_with_outro, index=None, key=processo_key,
                           format_func=lambda x: "Outro (digitar)" if x == PROCESSO_OUTRO else x)
    
    processo_custom = st.text_input("Nome do processo (novo)", key=processo_custom_key) if processo == PROCESSO_OUTRO else ""
    processo_selecionado = processo_custom.strip() if processo == PROCESSO_OUTRO else processo
    
    data_producao = st.date_input("Data", value=date.today(), format="DD/MM/YYYY", key=data_producao_key)
    hora_iniciada = st.time_input("Hora início", value=time(0,0), key=hora_iniciada_key)
    hora_finalizada = st.time_input("Hora fim", value=time(0,0), key=hora_finalizada_key)
    quantidade_produzida = st.number_input("Quantidade", min_value=0, step=1, key=quantidade_produzida_key)
    pecas_mortas = st.number_input("Peças mortas", min_value=0, step=1, key=pecas_mortas_key)
    quantidade_total = st.number_input("Quantidade total", min_value=0, step=1, key=quantidade_total_key)
    numero_operadores = st.number_input("Num. operadores", min_value=1, step=1, key=numero_operadores_key)
    
    operadores_base = unique_preserve_order([o for o in operadores if o])
    operadores_selecionados = st.multiselect(f"Operadores ({len(st.session_state.operadores_selecionados)}/{numero_operadores})",
                                             operadores_base, key=operadores_multiselect_key,
                                             max_selections=numero_operadores)
    st.session_state.operadores_selecionados = operadores_selecionados
    
    save_col, success_col = st.columns([1, 8])
    with save_col:
        salvar = st.button("Salvar")
    with success_col:
        if success_message:
            st.success(success_message)

    if salvar:
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
                st.session_state[SAVE_SUCCESS_MESSAGE_KEY] = f"Salvo com sucesso! ID #{entry_id}"
                st.session_state[RESET_FORM_REQUESTED_KEY] = True
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
    st.dataframe(df, hide_index=True, width="stretch")
    
    csv = df.to_csv(index=False).encode('utf-8-sig')
    st.download_button("Exportar CSV", data=csv, file_name="registros.csv", mime="text/csv")
    
    st.markdown("</div>", unsafe_allow_html=True)

def format_entry_option(entry):
    return (
        f"#{entry.get('id')} | {entry.get('data_producao') or '-'} | "
        f"{entry.get('cliente') or '-'} | {entry.get('display') or '-'} | "
        f"{entry.get('processo') or '-'}"
    )

def entry_matches_query(entry, query):
    query = normalize_text(query).lower()
    if not query:
        return True
    searchable = [
        entry.get("id"),
        entry.get("cliente"),
        entry.get("display"),
        entry.get("numero_display"),
        entry.get("maquinario"),
        entry.get("processo"),
        entry.get("data_producao"),
        entry.get("operadores"),
    ]
    return any(query in normalize_text(value).lower() for value in searchable)

def render_ajustes_screen():
    st.markdown('<div class="form-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">Ajustar lancamento anterior</div>', unsafe_allow_html=True)

    success_message = st.session_state.pop(ADJUST_SUCCESS_MESSAGE_KEY, None)

    db = get_db()
    entries = db.get_all_entries()

    if not entries:
        st.info("Nenhum registro para ajustar.")
        st.markdown("</div>", unsafe_allow_html=True)
        return

    busca = st.text_input(
        "Buscar",
        placeholder="ID, cliente, display, codigo, ferramental, processo ou operador",
        key="adjust_search",
    )
    filtered_entries = [entry for entry in entries if entry_matches_query(entry, busca)]

    if not filtered_entries:
        st.warning("Nenhum lancamento encontrado para esse filtro.")
        st.markdown("</div>", unsafe_allow_html=True)
        return

    preview_columns = [
        "id",
        "data_producao",
        "cliente",
        "display",
        "numero_display",
        "maquinario",
        "processo",
        "quantidade",
        "pecas_mortas",
        "quantidade_total",
        "operadores",
    ]
    preview_df = pd.DataFrame(filtered_entries[:50])
    visible_columns = [col for col in preview_columns if col in preview_df.columns]
    st.dataframe(preview_df[visible_columns], hide_index=True, width="stretch")
    if len(filtered_entries) > 50:
        st.caption("Mostrando os 50 primeiros resultados do filtro.")

    entry_options = filtered_entries[:200]
    selected_entry_id = st.selectbox(
        "Lancamento para ajustar",
        [entry["id"] for entry in entry_options],
        format_func=lambda entry_id: format_entry_option(
            next(entry for entry in entry_options if entry["id"] == entry_id)
        ),
        key="adjust_selected_entry_id",
    )
    selected_entry = next(entry for entry in entry_options if entry["id"] == selected_entry_id)
    key_base = f"{ADJUST_FIELD_PREFIX}{selected_entry_id}"

    cliente_key = f"{key_base}__cliente"
    acabado_key = f"{key_base}__acabado"
    numero_display_key = f"{key_base}__numero_display"
    ferramental_key = f"{key_base}__ferramental"
    processo_key = f"{key_base}__processo"
    processo_custom_key = f"{key_base}__processo_custom"
    data_producao_key = f"{key_base}__data_producao"
    hora_iniciada_key = f"{key_base}__hora_iniciada"
    hora_finalizada_key = f"{key_base}__hora_finalizada"
    quantidade_produzida_key = f"{key_base}__quantidade_produzida"
    pecas_mortas_key = f"{key_base}__pecas_mortas"
    quantidade_total_key = f"{key_base}__quantidade_total"
    numero_operadores_key = f"{key_base}__numero_operadores"
    operadores_multiselect_key = f"{key_base}__operadores_multiselect"

    cliente_atual = st.session_state.get(cliente_key, selected_entry.get("cliente"))
    cliente_options = add_current_option(choices["clientes"], cliente_atual)
    cliente = st.selectbox(
        "Cliente",
        cliente_options,
        index=option_index(cliente_options, cliente_atual),
        key=cliente_key,
    )

    acabado_atual = st.session_state.get(acabado_key, selected_entry.get("display"))
    acabado_base_options = get_acabados_for_cliente(cliente) if cliente else choices["acabados"]
    acabado_options = add_current_option(acabado_base_options, acabado_atual)
    acabado = st.selectbox(
        "Display",
        acabado_options,
        index=option_index(acabado_options, acabado_atual),
        key=acabado_key,
    )

    numero_display = st.text_input(
        "Codigo (8 digitos)",
        value=normalize_text(selected_entry.get("numero_display")),
        key=numero_display_key,
        max_chars=8,
    )

    ferramental_atual = st.session_state.get(ferramental_key, selected_entry.get("maquinario"))
    ferramental_options = add_current_option(choices["ferramentais"], ferramental_atual)
    ferramental = st.selectbox(
        "Ferramental",
        ferramental_options,
        index=option_index(ferramental_options, ferramental_atual),
        key=ferramental_key,
    )

    processo_atual = st.session_state.get(processo_key, selected_entry.get("processo"))
    processo_base_options = get_process_choices_for_acabado_e_ferramental(acabado, ferramental)
    processo_options = add_current_option(processo_base_options, processo_atual)
    processo_options = unique_preserve_order(processo_options + [PROCESSO_OUTRO])
    processo = st.selectbox(
        "Processo",
        processo_options,
        index=option_index(processo_options, processo_atual),
        key=processo_key,
        format_func=lambda x: "Outro (digitar)" if x == PROCESSO_OUTRO else x,
    )
    processo_custom = (
        st.text_input("Nome do processo (novo)", key=processo_custom_key)
        if processo == PROCESSO_OUTRO
        else ""
    )
    processo_selecionado = processo_custom.strip() if processo == PROCESSO_OUTRO else processo

    data_producao = st.date_input(
        "Data",
        value=parse_date_value(selected_entry.get("data_producao")),
        format="DD/MM/YYYY",
        key=data_producao_key,
    )
    hora_iniciada = st.time_input(
        "Hora inicio",
        value=parse_time_value(selected_entry.get("hora_inicio")),
        key=hora_iniciada_key,
    )
    hora_finalizada = st.time_input(
        "Hora fim",
        value=parse_time_value(selected_entry.get("hora_fim")),
        key=hora_finalizada_key,
    )
    quantidade_produzida = st.number_input(
        "Quantidade",
        min_value=0,
        step=1,
        value=int(selected_entry.get("quantidade") or 0),
        key=quantidade_produzida_key,
    )
    pecas_mortas = st.number_input(
        "Pecas mortas",
        min_value=0,
        step=1,
        value=int(selected_entry.get("pecas_mortas") or 0),
        key=pecas_mortas_key,
    )
    quantidade_total = st.number_input(
        "Quantidade total",
        min_value=0,
        step=1,
        value=int(selected_entry.get("quantidade_total") or 0),
        key=quantidade_total_key,
    )
    numero_operadores = st.number_input(
        "Num. operadores",
        min_value=1,
        step=1,
        value=max(1, int(selected_entry.get("numero_operadores") or 1)),
        key=numero_operadores_key,
    )

    operadores_atual = st.session_state.get(
        operadores_multiselect_key,
        split_operadores(selected_entry.get("operadores")),
    )
    operadores_options = unique_preserve_order(operadores_atual + [o for o in operadores if o])
    operadores_selecionados = st.multiselect(
        f"Operadores ({len(operadores_atual)}/{numero_operadores})",
        operadores_options,
        default=operadores_atual,
        key=operadores_multiselect_key,
    )

    save_col, success_col = st.columns([1, 8])
    with save_col:
        salvar_ajuste = st.button("Salvar ajuste", key=f"{key_base}__save")
    with success_col:
        if success_message:
            st.success(success_message)

    if salvar_ajuste:
        erros = validate_inputs(
            cliente,
            acabado,
            numero_display,
            ferramental,
            processo_selecionado,
            data_producao,
            hora_iniciada,
            hora_finalizada,
            quantidade_produzida,
            quantidade_total,
            numero_operadores,
            operadores_selecionados,
        )
        if erros:
            st.error("Erros:\n- " + "\n- ".join(erros))
        else:
            registro = {
                "cliente": cliente,
                "acabado": acabado,
                "numero_display": str(numero_display).strip(),
                "ferramental": ferramental,
                "processo": processo_selecionado,
                "data_producao": data_producao.strftime("%d/%m/%y"),
                "operadores": operadores_selecionados,
                "hora_iniciada": hora_iniciada.strftime("%H:%M"),
                "hora_finalizada": hora_finalizada.strftime("%H:%M"),
                "quantidade_produzida": quantidade_produzida,
                "pecas_mortas": pecas_mortas,
                "numero_operadores": numero_operadores,
                "quantidade_total": quantidade_total,
            }
            try:
                update_data = build_entry_update_payload_from_streamlit(
                    registro,
                    selected_entry,
                    SCHEMA_VERSION,
                )
                updated = db.update_entry(selected_entry_id, update_data)
            except Exception as exc:
                st.error(f"Erro ao salvar ajuste: {exc}")
            else:
                if updated:
                    st.session_state[ADJUST_SUCCESS_MESSAGE_KEY] = (
                        f"Lancamento #{selected_entry_id} ajustado com sucesso."
                    )
                    st.rerun()
                else:
                    st.error("Nao foi possivel encontrar esse lancamento para atualizar.")

    st.markdown("</div>", unsafe_allow_html=True)

tab1, tab2, tab3 = st.tabs(["📝 Lançamento", "✏️ Ajustes", "📊 Consulta"])
with tab1:
    render_lancamento_screen()
with tab2:
    render_ajustes_screen()
with tab3:
    render_consulta_screen()

st.divider()
st.caption("FORMS-MTECH v1.2 - Refatorado para Streamlit Cloud")
