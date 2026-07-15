"""FORMS-MTECH - Controle de Produção
Versão refatorada sem Django, compatível com Streamlit Cloud"""

from datetime import datetime, time, date
import ast
import base64
import hashlib
import hmac
from io import BytesIO
import os
import re
import secrets as secrets_lib
from pathlib import Path

import pandas as pd
import streamlit as st

from core.db_utils import (
    build_entry_update_payload_from_streamlit,
    build_entry_payload_from_streamlit,
    build_painting_entry_payload_from_streamlit,
    get_db,
    is_cloud_runtime,
)
from core.excel_utils import (
    get_acabados_for_cliente,
    get_painting_choices,
    get_painting_process_choices,
    get_process_by_id,
    get_process_choices_for_acabado_e_ferramental,
    get_unique_choices,
    get_operadores,
)
from core.qr_utils import extract_process_id, is_painting_process
from core.qr_browser import qr_browser_scanner

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

SCHEMA_VERSION = "1.2"
PROCESSO_OUTRO = "__PROCESSO_OUTRO__"
AUTH_SESSION_KEY = "auth_authenticated"
AUTH_USER_KEY = "auth_user"
SAVE_SUCCESS_MESSAGE_KEY = "save_success_message"
ADJUST_SUCCESS_MESSAGE_KEY = "adjust_success_message"
PAINTING_ADJUST_SUCCESS_MESSAGE_KEY = "painting_adjust_success_message"
RESET_FORM_REQUESTED_KEY = "reset_form_requested"
FORM_VERSION_KEY = "form_version"
FORM_FIELD_PREFIX = "form_field__"
QR_INPUT_KEY = "qr_process_input"
QR_CONTEXT_KEY = "qr_process_context"
QR_ERROR_KEY = "qr_process_error"
QR_INPUT_RESET_REQUESTED_KEY = "qr_input_reset_requested"
QR_FOCUS_REQUESTED_KEY = "qr_focus_requested"
QR_LAST_QUERY_KEY = "qr_last_query"
PAINTING_QR_INPUT_KEY = "painting_qr_process_input"
PAINTING_QR_CONTEXT_KEY = "painting_qr_process_context"
PAINTING_QR_ERROR_KEY = "painting_qr_process_error"
PAINTING_QR_INPUT_RESET_REQUESTED_KEY = "painting_qr_input_reset_requested"
PAINTING_QR_FOCUS_REQUESTED_KEY = "painting_qr_focus_requested"
PAINTING_FORM_VERSION_KEY = "painting_form_version"
PAINTING_FORM_FIELD_PREFIX = "painting_form_field__"
PAINTING_SAVE_SUCCESS_MESSAGE_KEY = "painting_save_success_message"
PAINTING_RESET_FORM_REQUESTED_KEY = "painting_reset_form_requested"
ADJUST_FIELD_PREFIX = "adjust_field__"
PAINTING_ADJUST_FIELD_PREFIX = "painting_adjust_field__"
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

def build_password_hash(password: str, salt: str | None = None, iterations: int = 260000) -> str:
    salt = salt or secrets_lib.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        iterations,
    ).hex()
    return f"pbkdf2_sha256${iterations}${salt}${digest}"

def verify_password(password: str, stored_password: str) -> bool:
    stored_password = str(stored_password or "")
    if stored_password.startswith("pbkdf2_sha256$"):
        try:
            _algorithm, iterations, salt, expected = stored_password.split("$", 3)
            candidate = build_password_hash(password, salt=salt, iterations=int(iterations))
            candidate_hash = candidate.rsplit("$", 1)[-1]
        except (TypeError, ValueError):
            return False
        return hmac.compare_digest(candidate_hash, expected)
    return hmac.compare_digest(password, stored_password)

def _get_auth_secret(key: str):
    try:
        auth_config = st.secrets.get("auth", {})
        if key in auth_config:
            return auth_config.get(key)
    except Exception:
        pass
    return os.getenv(f"AUTH_{key.upper()}")

def get_auth_users() -> dict:
    users = {}
    try:
        auth_config = st.secrets.get("auth", {})
        configured_users = auth_config.get("users", {})
        if hasattr(configured_users, "items"):
            users.update({str(user): str(password) for user, password in configured_users.items()})
    except Exception:
        pass

    username = _get_auth_secret("username")
    password_hash = _get_auth_secret("password_hash")
    password = _get_auth_secret("password")
    if username and (password_hash or password):
        users[str(username)] = str(password_hash or password)

    return users

def render_login_screen(users: dict) -> None:
    st.markdown('<div class="form-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">Acesso restrito</div>', unsafe_allow_html=True)

    if not users:
        st.error("Login nao configurado. Configure usuario e senha nos Secrets do Streamlit Cloud.")
        st.code(
            '[auth]\n'
            'username = "seu_usuario"\n'
            'password_hash = "pbkdf2_sha256$..."',
            language="toml",
        )
        st.markdown("</div>", unsafe_allow_html=True)
        return

    with st.form("login_form"):
        username = st.text_input("Usuario")
        password = st.text_input("Senha", type="password")
        entrar = st.form_submit_button("Entrar")

    if entrar:
        stored_password = users.get(username)
        if stored_password and verify_password(password, stored_password):
            st.session_state[AUTH_SESSION_KEY] = True
            st.session_state[AUTH_USER_KEY] = username
            st.rerun()
        else:
            st.error("Usuario ou senha invalidos.")

    st.markdown("</div>", unsafe_allow_html=True)

def require_authentication() -> None:
    if st.session_state.get(AUTH_SESSION_KEY):
        return
    render_login_screen(get_auth_users())
    st.stop()

def render_logout_control() -> None:
    user = st.session_state.get(AUTH_USER_KEY, "")
    col_user, col_button = st.columns([8, 1])
    with col_user:
        if user:
            st.caption(f"Usuario: {user}")
    with col_button:
        if st.button("Sair"):
            st.session_state.pop(AUTH_SESSION_KEY, None)
            st.session_state.pop(AUTH_USER_KEY, None)
            st.rerun()

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

def salvar_registro_pintura(payload: dict):
    try:
        registro = build_painting_entry_payload_from_streamlit(payload, SCHEMA_VERSION)
        return get_db().save_painting_entry(registro), None
    except Exception as exc:
        return None, f"Erro: {str(exc)}"

def render_header():
    logo_b64 = load_image_base64(LOGO_PATH)
    logo_img = f'<img src="data:image/png;base64,{logo_b64}" />' if logo_b64 else '<div class="logo-fallback">MTECH</div>'
    st.markdown(f'''<div class="app-hero">{logo_img}<div class="hero-text"><h1>Controle Produção</h1><p>MTECH</p></div></div>''', unsafe_allow_html=True)

render_header()
require_authentication()

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

choices = load_base_choices()
operadores = get_operadores()

if "last_ferramental" not in st.session_state:
    st.session_state.last_ferramental = None
if "last_cliente" not in st.session_state:
    st.session_state.last_cliente = None
if "operadores_selecionados" not in st.session_state:
    st.session_state.operadores_selecionados = []
if "last_painting_cliente" not in st.session_state:
    st.session_state.last_painting_cliente = None
if "last_painting_display" not in st.session_state:
    st.session_state.last_painting_display = None
if FORM_VERSION_KEY not in st.session_state:
    st.session_state[FORM_VERSION_KEY] = 0
if QR_FOCUS_REQUESTED_KEY not in st.session_state:
    st.session_state[QR_FOCUS_REQUESTED_KEY] = True
if PAINTING_QR_FOCUS_REQUESTED_KEY not in st.session_state:
    st.session_state[PAINTING_QR_FOCUS_REQUESTED_KEY] = False
if PAINTING_FORM_VERSION_KEY not in st.session_state:
    st.session_state[PAINTING_FORM_VERSION_KEY] = 0

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
    st.session_state.pop(QR_CONTEXT_KEY, None)
    st.session_state.pop(QR_ERROR_KEY, None)
    st.session_state.pop(QR_INPUT_KEY, None)
    st.session_state.pop(QR_INPUT_RESET_REQUESTED_KEY, None)
    st.session_state[QR_FOCUS_REQUESTED_KEY] = True

def form_key(name: str) -> str:
    return f"{FORM_FIELD_PREFIX}{st.session_state[FORM_VERSION_KEY]}__{name}"


def load_qr_process(raw_value) -> None:
    """Resolve o conteúdo lido e guarda somente dados consultados na base."""
    try:
        processo_id = extract_process_id(raw_value)
        process_data = get_process_by_id(processo_id)
        if process_data is None:
            raise ValueError(f"PROCESSO_ID não encontrado: {processo_id}")
        if is_painting_process(process_data):
            raise ValueError("Este QR Code pertence aos lançamentos de pintura.")
    except (OSError, ValueError) as exc:
        st.session_state.pop(QR_CONTEXT_KEY, None)
        st.session_state[QR_ERROR_KEY] = str(exc)
        st.session_state[QR_FOCUS_REQUESTED_KEY] = True
    else:
        st.session_state[QR_CONTEXT_KEY] = process_data
        st.session_state.pop(QR_ERROR_KEY, None)
        for field in ("cliente", "acabado", "ferramental", "processo", "processo_custom"):
            st.session_state.pop(form_key(field), None)
        st.session_state.last_cliente = None
        st.session_state.last_ferramental = None
    finally:
        st.session_state[QR_INPUT_RESET_REQUESTED_KEY] = True


def handle_qr_scan() -> None:
    load_qr_process(st.session_state.get(QR_INPUT_KEY, ""))


def load_painting_qr_process(raw_value) -> None:
    """Resolve um QR de pintura e guarda apenas os dados atuais da base."""
    try:
        processo_id = extract_process_id(raw_value)
        process_data = get_process_by_id(processo_id)
        if process_data is None:
            raise ValueError(f"PROCESSO_ID não encontrado: {processo_id}")
        if not is_painting_process(process_data):
            raise ValueError("Este QR Code não pertence aos lançamentos de pintura.")
    except (OSError, ValueError) as exc:
        st.session_state.pop(PAINTING_QR_CONTEXT_KEY, None)
        st.session_state[PAINTING_QR_ERROR_KEY] = str(exc)
        st.session_state[PAINTING_QR_FOCUS_REQUESTED_KEY] = True
    else:
        st.session_state[PAINTING_QR_CONTEXT_KEY] = process_data
        st.session_state.pop(PAINTING_QR_ERROR_KEY, None)
        for field in ("cliente", "display", "ferramental", "processo"):
            st.session_state.pop(painting_form_key(field), None)
        st.session_state.last_painting_cliente = None
        st.session_state.last_painting_display = None
    finally:
        st.session_state[PAINTING_QR_INPUT_RESET_REQUESTED_KEY] = True


def handle_painting_qr_scan() -> None:
    load_painting_qr_process(st.session_state.get(PAINTING_QR_INPUT_KEY, ""))


def load_qr_query_param() -> None:
    query_value = st.query_params.get("processo_id")
    if isinstance(query_value, list):
        query_value = query_value[0] if query_value else None
    if query_value in (None, ""):
        return

    marker = str(query_value).strip()
    if st.session_state.get(QR_LAST_QUERY_KEY) == marker:
        return
    st.session_state[QR_LAST_QUERY_KEY] = marker
    try:
        processo_id = extract_process_id(marker)
        process_data = get_process_by_id(processo_id)
    except (OSError, ValueError):
        load_qr_process(marker)
        return

    if is_painting_process(process_data):
        load_painting_qr_process(marker)
    else:
        load_qr_process(marker)


def configure_qr_input(should_focus: bool, input_label: str) -> None:
    """Devolve o foco ao leitor depois de abrir ou limpar o formulário."""
    focus_value = "true" if should_focus else "false"
    st.iframe(
        f"""
        <script>
        setTimeout(() => {{
            const input = window.parent.document.querySelector(
                'input[aria-label="{input_label}"]'
            );
            if (input) {{
                if (input.dataset.qrEnterBlurBoundV2 !== 'true') {{
                    input.dataset.qrEnterBlurBoundV2 = 'true';
                    input.addEventListener('keydown', (event) => {{
                        if (event.key === 'Enter') {{
                            event.preventDefault();
                            event.stopImmediatePropagation();
                            input.blur();
                        }}
                    }}, true);
                }}
                if ({focus_value}) {{
                    input.focus();
                    input.select();
                }}
            }}
        }}, 150);
        </script>
        """,
        height=1,
        width="content",
        tab_index=-1,
    )


def render_qr_browser_reader(*, component_key: str, on_detect) -> None:
    """Lê o QR no navegador e envia somente o texto decodificado ao backend."""
    with st.expander("Ler QR Code pela câmera do celular"):
        st.caption(
            "A leitura acontece neste aparelho. Nenhuma imagem ou transmissão "
            "de vídeo é enviada ao servidor."
        )
        value = qr_browser_scanner(key=component_key)
        if value:
            on_detect(value)
            st.rerun()


def reset_painting_form_fields():
    for key in list(st.session_state.keys()):
        if isinstance(key, str) and key.startswith(PAINTING_FORM_FIELD_PREFIX):
            st.session_state.pop(key, None)
    st.session_state[PAINTING_FORM_VERSION_KEY] += 1
    st.session_state.last_painting_cliente = None
    st.session_state.last_painting_display = None
    st.session_state.pop(PAINTING_QR_CONTEXT_KEY, None)
    st.session_state.pop(PAINTING_QR_ERROR_KEY, None)
    st.session_state.pop(PAINTING_QR_INPUT_KEY, None)
    st.session_state.pop(PAINTING_QR_INPUT_RESET_REQUESTED_KEY, None)
    st.session_state[PAINTING_QR_FOCUS_REQUESTED_KEY] = True

def painting_form_key(name: str) -> str:
    return f"{PAINTING_FORM_FIELD_PREFIX}{st.session_state[PAINTING_FORM_VERSION_KEY]}__{name}"

def render_lancamento_screen():
    if st.session_state.pop(RESET_FORM_REQUESTED_KEY, False):
        reset_form_fields()

    load_qr_query_param()
    if st.session_state.pop(QR_INPUT_RESET_REQUESTED_KEY, False):
        st.session_state[QR_INPUT_KEY] = ""

    st.markdown('<div class="form-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">Lançamento</div>', unsafe_allow_html=True)

    success_message = st.session_state.pop(SAVE_SUCCESS_MESSAGE_KEY, None)
    should_focus_qr = st.session_state.pop(QR_FOCUS_REQUESTED_KEY, False)

    st.text_input(
        "Ler QR Code ou informar ID do processo",
        key=QR_INPUT_KEY,
        placeholder="Ex.: 000001",
        on_change=handle_qr_scan,
    )
    st.caption("O leitor USB pode enviar somente o ID ou a URL completa do processo.")
    configure_qr_input(should_focus_qr, "Ler QR Code ou informar ID do processo")

    qr_error = st.session_state.get(QR_ERROR_KEY)
    if qr_error:
        st.error(qr_error)

    qr_process = st.session_state.get(QR_CONTEXT_KEY)
    if qr_process is None:
        render_qr_browser_reader(
            component_key="qr-browser-reader",
            on_detect=load_qr_process,
        )

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

    if qr_process:
        st.success(f"Processo {qr_process['processo_id']} identificado pelo QR Code.")
        with st.container(border=True):
            left_column, right_column = st.columns(2)
            with left_column:
                st.markdown(f"**Cliente:** {qr_process['cliente']}")
                st.markdown(f"**Display:** {qr_process['acabado']}")
            with right_column:
                st.markdown(f"**Ferramental:** {qr_process['ferramental']}")
                st.markdown(f"**Processo:** {qr_process['processo']}")
        if st.button("Alterar dados manualmente", key=form_key("use_manual_data")):
            st.session_state.pop(QR_CONTEXT_KEY, None)
            st.session_state.pop(QR_ERROR_KEY, None)
            st.session_state[QR_INPUT_RESET_REQUESTED_KEY] = True
            st.rerun()

        cliente = qr_process["cliente"]
        acabado = qr_process["acabado"]
        ferramental = qr_process["ferramental"]
        processo_selecionado = qr_process["processo"]
    else:
        cliente = st.selectbox("Cliente", choices["clientes"], index=None, key=cliente_key)
        if st.session_state.last_cliente != cliente:
            st.session_state.pop(acabado_key, None)
        st.session_state.last_cliente = cliente

        acabado_options = get_acabados_for_cliente(cliente) if cliente else choices["acabados"]
        acabado = st.selectbox("Display", acabado_options, index=None, key=acabado_key)

        ferramental = st.selectbox("Ferramental", choices["ferramentais"], index=None, key=ferramental_key)

        if st.session_state.last_ferramental != ferramental:
            st.session_state.pop(processo_key, None)
        st.session_state.last_ferramental = ferramental

        processo_options = get_process_choices_for_acabado_e_ferramental(acabado, ferramental)
        processo_options_with_outro = processo_options + [PROCESSO_OUTRO]
        processo = st.selectbox(
            "Processo",
            processo_options_with_outro,
            index=None,
            key=processo_key,
            format_func=lambda x: "Outro (digitar)" if x == PROCESSO_OUTRO else x,
        )

        processo_custom = (
            st.text_input("Nome do processo (novo)", key=processo_custom_key)
            if processo == PROCESSO_OUTRO
            else ""
        )
        processo_selecionado = processo_custom.strip() if processo == PROCESSO_OUTRO else processo

    numero_display = st.text_input("Codigo (8 digitos)", key=numero_display_key, max_chars=8)
    
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
        salvar = st.button("Salvar e ler próximo")
    with success_col:
        if success_message:
            st.success(success_message)

    if salvar:
        if qr_process:
            try:
                refreshed_process = get_process_by_id(qr_process["processo_id"])
                if refreshed_process is None:
                    raise ValueError(
                        f"PROCESSO_ID não encontrado: {qr_process['processo_id']}"
                    )
            except (OSError, ValueError) as exc:
                st.error(f"Não foi possível validar novamente o QR: {exc}")
                st.stop()
            cliente = refreshed_process["cliente"]
            acabado = refreshed_process["acabado"]
            ferramental = refreshed_process["ferramental"]
            processo_selecionado = refreshed_process["processo"]

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

def render_lancamento_pintura_screen():
    if st.session_state.pop(PAINTING_RESET_FORM_REQUESTED_KEY, False):
        reset_painting_form_fields()
    if st.session_state.pop(PAINTING_QR_INPUT_RESET_REQUESTED_KEY, False):
        st.session_state[PAINTING_QR_INPUT_KEY] = ""

    st.markdown('<div class="form-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">Lançamentos pintura</div>', unsafe_allow_html=True)
    success_message = st.session_state.pop(PAINTING_SAVE_SUCCESS_MESSAGE_KEY, None)
    should_focus_qr = st.session_state.pop(PAINTING_QR_FOCUS_REQUESTED_KEY, False)
    painting_qr_label = "Ler QR Code de pintura ou informar ID do processo"

    st.text_input(
        painting_qr_label,
        key=PAINTING_QR_INPUT_KEY,
        placeholder="Ex.: 001123",
        on_change=handle_painting_qr_scan,
    )
    st.caption("O leitor USB pode enviar somente o ID ou a URL completa do processo.")
    configure_qr_input(should_focus_qr, painting_qr_label)

    painting_qr_error = st.session_state.get(PAINTING_QR_ERROR_KEY)
    if painting_qr_error:
        st.error(painting_qr_error)

    painting_qr_process = st.session_state.get(PAINTING_QR_CONTEXT_KEY)
    if painting_qr_process is None:
        render_qr_browser_reader(
            component_key="painting-qr-browser-reader",
            on_detect=load_painting_qr_process,
        )

    if painting_qr_process:
        st.success(
            f"Processo {painting_qr_process['processo_id']} identificado pelo QR Code."
        )
        with st.container(border=True):
            left_column, right_column = st.columns(2)
            with left_column:
                st.markdown(f"**Cliente:** {painting_qr_process['cliente']}")
                st.markdown(f"**Display:** {painting_qr_process['acabado']}")
            with right_column:
                st.markdown(f"**Ferramental:** {painting_qr_process['ferramental']}")
                st.markdown(f"**Processo:** {painting_qr_process['processo']}")

        if st.button(
            "Alterar dados manualmente",
            key=painting_form_key("use_manual_data"),
        ):
            st.session_state.pop(PAINTING_QR_CONTEXT_KEY, None)
            st.session_state.pop(PAINTING_QR_ERROR_KEY, None)
            st.session_state[PAINTING_QR_INPUT_RESET_REQUESTED_KEY] = True
            st.rerun()

        cliente = painting_qr_process["cliente"]
        display = painting_qr_process["acabado"]
        ferramental = painting_qr_process["ferramental"]
        processo = painting_qr_process["processo"]
    else:
        cliente = st.selectbox(
            "Cliente", get_painting_choices("CLIENTE"), index=None,
            key=painting_form_key("cliente"),
        )
        if st.session_state.last_painting_cliente != cliente:
            for field in ("display", "ferramental", "processo"):
                st.session_state.pop(painting_form_key(field), None)
        st.session_state.last_painting_cliente = cliente
        display = st.selectbox(
            "Display", get_painting_choices("ACABADO", CLIENTE=cliente), index=None,
            key=painting_form_key("display"),
        )
        if st.session_state.last_painting_display != display:
            for field in ("ferramental", "processo"):
                st.session_state.pop(painting_form_key(field), None)
        st.session_state.last_painting_display = display
        ferramental = st.selectbox(
            "Ferramental", get_painting_choices("FERRAMENTAL", CLIENTE=cliente, ACABADO=display),
            index=None, key=painting_form_key("ferramental"),
        )
        processo = st.selectbox(
            "Processo", get_painting_process_choices(cliente, display, ferramental), index=None,
            key=painting_form_key("processo"),
        )

    numero_display = st.text_input(
        "Codigo (8 digitos)", max_chars=8, key=painting_form_key("numero_display"),
    )
    codigo_pintura = st.text_input("Código pintura", key=painting_form_key("codigo_pintura"))
    data_producao = st.date_input(
        "Data", value=date.today(), format="DD/MM/YYYY", key=painting_form_key("data_producao"),
    )
    hora_lancamento = st.time_input(
        "Hora do lançamento", value=time(0, 0), key=painting_form_key("hora_lancamento"),
    )
    quantidade = st.number_input("Quantidade", min_value=0, step=1, key=painting_form_key("quantidade"))
    quantidade_total = st.number_input(
        "Quantidade total", min_value=0, step=1, key=painting_form_key("quantidade_total"),
    )

    save_col, success_col = st.columns([1, 8])
    with save_col:
        salvar = st.button("Salvar e ler próximo", key="save_painting_entry")
    with success_col:
        if success_message:
            st.success(success_message)

    if salvar:
        if painting_qr_process:
            try:
                refreshed_process = get_process_by_id(
                    painting_qr_process["processo_id"]
                )
                if refreshed_process is None:
                    raise ValueError(
                        f"PROCESSO_ID não encontrado: "
                        f"{painting_qr_process['processo_id']}"
                    )
                if not is_painting_process(refreshed_process):
                    raise ValueError("O processo não pertence à base de pintura.")
            except (OSError, ValueError) as exc:
                st.error(f"Não foi possível validar novamente o QR: {exc}")
                st.stop()

            cliente = refreshed_process["cliente"]
            display = refreshed_process["acabado"]
            ferramental = refreshed_process["ferramental"]
            processo = refreshed_process["processo"]

        obrigatorios = [
            (cliente, "Cliente"), (display, "Display"), (numero_display, "Codigo"),
            (codigo_pintura, "Código pintura"), (ferramental, "Ferramental"), (processo, "Processo"),
        ]
        erros = [f"{label} obrigatorio." for value, label in obrigatorios if not value]
        if numero_display and not re.fullmatch(r"\d{8}", str(numero_display).strip()):
            erros.append("Codigo deve ter 8 digitos.")
        if quantidade_total < quantidade:
            erros.append("Quantidade total deve ser >= quantidade.")

        if erros:
            st.error("Erros:\n- " + "\n- ".join(erros))
        else:
            entry_id, error = salvar_registro_pintura({
                "cliente": cliente,
                "display": display,
                "numero_display": numero_display,
                "codigo_pintura": codigo_pintura,
                "ferramental": ferramental,
                "processo": processo,
                "data_producao": data_producao.strftime("%d/%m/%y"),
                "hora_lancamento": hora_lancamento.strftime("%H:%M"),
                "quantidade": quantidade,
                "quantidade_total": quantidade_total,
            })
            if entry_id:
                st.session_state[PAINTING_SAVE_SUCCESS_MESSAGE_KEY] = f"Salvo com sucesso! ID #{entry_id}"
                st.session_state[PAINTING_RESET_FORM_REQUESTED_KEY] = True
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

def painting_entry_matches_query(entry, query):
    query = normalize_text(query).lower()
    if not query:
        return True
    searchable = [
        entry.get("id"),
        entry.get("cliente"),
        entry.get("display"),
        entry.get("numero_display"),
        entry.get("codigo_pintura"),
        entry.get("maquinario"),
        entry.get("processo"),
        entry.get("data_producao"),
    ]
    return any(query in normalize_text(value).lower() for value in searchable)


def format_painting_entry_option(entry):
    return (
        f"#{entry.get('id')} | {entry.get('data_producao') or '-'} | "
        f"{entry.get('cliente') or '-'} | {entry.get('display') or '-'} | "
        f"{entry.get('codigo_pintura') or '-'} | {entry.get('processo') or '-'}"
    )


def render_ajustes_pintura_screen():
    st.markdown('<div class="form-card">', unsafe_allow_html=True)
    st.markdown(
        '<div class="section-title">Ajustar lançamento de pintura</div>',
        unsafe_allow_html=True,
    )

    success_message = st.session_state.pop(PAINTING_ADJUST_SUCCESS_MESSAGE_KEY, None)
    db = get_db()
    entries = db.get_all_painting_entries()

    if not entries:
        st.info("Nenhum lançamento de pintura para ajustar.")
        st.markdown("</div>", unsafe_allow_html=True)
        return

    busca = st.text_input(
        "Buscar lançamento de pintura",
        placeholder=(
            "ID, cliente, display, código, código pintura, ferramental ou processo"
        ),
        key="painting_adjust_search",
    )
    filtered_entries = [
        entry for entry in entries if painting_entry_matches_query(entry, busca)
    ]

    if not filtered_entries:
        st.warning("Nenhum lançamento de pintura encontrado para esse filtro.")
        st.markdown("</div>", unsafe_allow_html=True)
        return

    preview_columns = [
        "id",
        "data_producao",
        "hora_lancamento",
        "cliente",
        "display",
        "numero_display",
        "codigo_pintura",
        "maquinario",
        "processo",
        "quantidade",
        "quantidade_total",
    ]
    preview_df = pd.DataFrame(filtered_entries[:50])
    visible_columns = [col for col in preview_columns if col in preview_df.columns]
    st.dataframe(preview_df[visible_columns], hide_index=True, width="stretch")
    if len(filtered_entries) > 50:
        st.caption("Mostrando os 50 primeiros resultados do filtro.")

    entry_options = filtered_entries[:200]
    selected_key = "painting_adjust_selected_entry_id"
    valid_ids = [entry["id"] for entry in entry_options]
    if st.session_state.get(selected_key) not in [None, *valid_ids]:
        st.session_state.pop(selected_key, None)
    selected_entry_id = st.selectbox(
        "Lançamento de pintura para ajustar",
        valid_ids,
        format_func=lambda entry_id: format_painting_entry_option(
            next(entry for entry in entry_options if entry["id"] == entry_id)
        ),
        key=selected_key,
    )
    selected_entry = next(
        entry for entry in entry_options if entry["id"] == selected_entry_id
    )
    key_base = f"{PAINTING_ADJUST_FIELD_PREFIX}{selected_entry_id}"

    cliente_atual = selected_entry.get("cliente")
    cliente_options = add_current_option(get_painting_choices("CLIENTE"), cliente_atual)
    cliente = st.selectbox(
        "Cliente",
        cliente_options,
        index=option_index(cliente_options, cliente_atual),
        key=f"{key_base}__cliente",
    )

    display_atual = selected_entry.get("display")
    display_options = add_current_option(
        get_painting_choices("ACABADO", CLIENTE=cliente), display_atual
    )
    display = st.selectbox(
        "Display",
        display_options,
        index=option_index(display_options, display_atual),
        key=f"{key_base}__display",
    )
    numero_display = st.text_input(
        "Código (8 dígitos)",
        value=normalize_text(selected_entry.get("numero_display")),
        max_chars=8,
        key=f"{key_base}__numero_display",
    )
    codigo_pintura = st.text_input(
        "Código pintura",
        value=normalize_text(selected_entry.get("codigo_pintura")),
        key=f"{key_base}__codigo_pintura",
    )

    ferramental_atual = selected_entry.get("maquinario")
    ferramental_options = add_current_option(
        get_painting_choices(
            "FERRAMENTAL", CLIENTE=cliente, ACABADO=display
        ),
        ferramental_atual,
    )
    ferramental = st.selectbox(
        "Ferramental",
        ferramental_options,
        index=option_index(ferramental_options, ferramental_atual),
        key=f"{key_base}__ferramental",
    )

    processo_atual = selected_entry.get("processo")
    processo_options = add_current_option(
        get_painting_process_choices(cliente, display, ferramental), processo_atual
    )
    processo = st.selectbox(
        "Processo",
        processo_options,
        index=option_index(processo_options, processo_atual),
        key=f"{key_base}__processo",
    )
    data_producao = st.date_input(
        "Data",
        value=parse_date_value(selected_entry.get("data_producao")),
        format="DD/MM/YYYY",
        key=f"{key_base}__data_producao",
    )
    hora_lancamento = st.time_input(
        "Hora do lançamento",
        value=parse_time_value(selected_entry.get("hora_lancamento")),
        key=f"{key_base}__hora_lancamento",
    )
    quantidade = st.number_input(
        "Quantidade",
        min_value=0,
        step=1,
        value=int(selected_entry.get("quantidade") or 0),
        key=f"{key_base}__quantidade",
    )
    quantidade_total = st.number_input(
        "Quantidade total",
        min_value=0,
        step=1,
        value=int(selected_entry.get("quantidade_total") or 0),
        key=f"{key_base}__quantidade_total",
    )

    save_col, success_col = st.columns([1, 8])
    with save_col:
        salvar_ajuste = st.button(
            "Salvar ajuste", key=f"{key_base}__save_painting"
        )
    with success_col:
        if success_message:
            st.success(success_message)

    if salvar_ajuste:
        obrigatorios = [
            (cliente, "Cliente"),
            (display, "Display"),
            (numero_display, "Código"),
            (codigo_pintura, "Código pintura"),
            (ferramental, "Ferramental"),
            (processo, "Processo"),
        ]
        erros = [
            f"{label} obrigatório." for value, label in obrigatorios if not value
        ]
        if numero_display and not re.fullmatch(
            r"\d{8}", str(numero_display).strip()
        ):
            erros.append("Código deve ter 8 dígitos.")
        if quantidade_total < quantidade:
            erros.append("Quantidade total deve ser >= quantidade.")

        if erros:
            st.error("Erros:\n- " + "\n- ".join(erros))
        else:
            registro = {
                "cliente": cliente,
                "display": display,
                "numero_display": numero_display,
                "codigo_pintura": codigo_pintura,
                "ferramental": ferramental,
                "processo": processo,
                "data_producao": data_producao.strftime("%d/%m/%y"),
                "hora_lancamento": hora_lancamento.strftime("%H:%M"),
                "quantidade": quantidade,
                "quantidade_total": quantidade_total,
            }
            try:
                update_data = build_painting_entry_payload_from_streamlit(
                    registro, SCHEMA_VERSION, existing_entry=selected_entry
                )
                updated = db.update_painting_entry(selected_entry_id, update_data)
            except Exception as exc:
                st.error(f"Erro ao salvar ajuste de pintura: {exc}")
            else:
                if updated:
                    st.session_state[PAINTING_ADJUST_SUCCESS_MESSAGE_KEY] = (
                        f"Lançamento de pintura #{selected_entry_id} ajustado com sucesso."
                    )
                    st.rerun()
                else:
                    st.error(
                        "Não foi possível encontrar esse lançamento de pintura."
                    )

    st.markdown("</div>", unsafe_allow_html=True)


def render_ajustes_producao_screen():
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


def render_ajustes_screen():
    tab_producao, tab_pintura_ajuste = st.tabs(["Produção", "Pintura"])
    with tab_producao:
        render_ajustes_producao_screen()
    with tab_pintura_ajuste:
        render_ajustes_pintura_screen()


render_logout_control()

tab1, tab_pintura, tab2, tab3 = st.tabs(
    ["📝 Lançamento", "🎨 Lançamentos pintura", "✏️ Ajustes", "📊 Consulta"]
)
with tab1:
    render_lancamento_screen()
with tab_pintura:
    render_lancamento_pintura_screen()
with tab2:
    render_ajustes_screen()
with tab3:
    render_consulta_screen()

st.divider()
st.caption("FORMS-MTECH v1.2 - Refatorado para Streamlit Cloud")
