"""
Database utilities - SQLite local e PostgreSQL persistente em producao.
"""

import hashlib
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

try:
    import psycopg
    from psycopg.rows import dict_row
except ImportError:  # pragma: no cover - usado apenas quando PostgreSQL nao esta instalado
    psycopg = None
    dict_row = None


ENV_DATABASE_KEYS = (
    "DATABASE_URL",
    "POSTGRES_URL",
    "POSTGRESQL_URL",
    "SUPABASE_DB_URL",
)


def _get_secret_value(key: str) -> Optional[str]:
    try:
        import streamlit as st

        value = st.secrets.get(key)
    except Exception:
        return None

    return str(value).strip() if value else None


def get_database_url() -> Optional[str]:
    """Busca URL persistente em variaveis de ambiente ou Streamlit Secrets."""
    for key in ENV_DATABASE_KEYS:
        value = os.getenv(key) or _get_secret_value(key)
        if value:
            return value
    return None


def _is_streamlit_cloud() -> bool:
    return Path("/app").exists() or bool(os.getenv("STREAMLIT_SHARING_MODE"))


def is_cloud_runtime() -> bool:
    """Indica se o app aparenta estar rodando no Streamlit Cloud."""
    return _is_streamlit_cloud()


def _normalize_postgres_url(database_url: str) -> str:
    if database_url.startswith("postgres://"):
        database_url = "postgresql://" + database_url[len("postgres://"):]

    parts = urlsplit(database_url)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    query.setdefault("sslmode", "require")
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


class ProductionDB:
    """Gerenciador de banco com PostgreSQL persistente ou SQLite local."""

    def __init__(
        self,
        db_path: Optional[str] = None,
        database_url: Optional[str] = None,
    ):
        self.database_url = database_url or get_database_url()
        self.backend = "postgres" if self.database_url else "sqlite"
        self.db_path: Optional[Path] = None

        if self.backend == "postgres":
            if psycopg is None:
                raise RuntimeError(
                    "DATABASE_URL configurada, mas a dependencia psycopg nao esta instalada."
                )
            self.database_url = _normalize_postgres_url(self.database_url)
        else:
            if db_path is None:
                db_path = str(Path.home() / ".mtech" / "production.db")
            self.db_path = Path(db_path)
            self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self._init_schema()

    @property
    def is_persistent(self) -> bool:
        return self.backend == "postgres"

    @property
    def placeholder(self) -> str:
        return "%s" if self.backend == "postgres" else "?"

    @contextmanager
    def get_conn(self):
        """Context manager para conexoes seguras."""
        if self.backend == "postgres":
            conn = psycopg.connect(self.database_url, row_factory=dict_row)
        else:
            conn = sqlite3.connect(str(self.db_path))
            conn.row_factory = sqlite3.Row

        try:
            yield conn
        finally:
            conn.close()

    def _init_schema(self):
        """Cria tabelas se nao existirem."""
        if self.backend == "postgres":
            self._init_postgres_schema()
        else:
            self._init_sqlite_schema()

    def _init_sqlite_schema(self):
        with self.get_conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS production_entries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    import_key TEXT UNIQUE,
                    source_hash TEXT UNIQUE,
                    schema_version TEXT,
                    timestamp DATETIME,
                    cliente TEXT,
                    display TEXT,
                    numero_display TEXT,
                    maquinario TEXT,
                    processo TEXT,
                    data_producao TEXT,
                    operadores TEXT,
                    numero_operadores INTEGER,
                    hora_inicio TEXT,
                    hora_fim TEXT,
                    quantidade INTEGER DEFAULT 0,
                    pecas_mortas INTEGER DEFAULT 0,
                    quantidade_total INTEGER DEFAULT 0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_timestamp
                ON production_entries(timestamp DESC)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_source_hash
                ON production_entries(source_hash)
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS painting_entries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    schema_version TEXT,
                    timestamp DATETIME,
                    cliente TEXT,
                    display TEXT,
                    numero_display TEXT,
                    codigo_pintura TEXT,
                    maquinario TEXT,
                    processo TEXT,
                    data_producao TEXT,
                    hora_lancamento TEXT,
                    quantidade INTEGER DEFAULT 0,
                    quantidade_total INTEGER DEFAULT 0,
                    source_hash TEXT UNIQUE,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_painting_timestamp
                ON painting_entries(timestamp DESC)
            """)
            conn.commit()

    def _init_postgres_schema(self):
        with self.get_conn() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS production_entries (
                        id BIGSERIAL PRIMARY KEY,
                        import_key TEXT UNIQUE,
                        source_hash TEXT UNIQUE,
                        schema_version TEXT,
                        timestamp TIMESTAMPTZ,
                        cliente TEXT,
                        display TEXT,
                        numero_display TEXT,
                        maquinario TEXT,
                        processo TEXT,
                        data_producao TEXT,
                        operadores TEXT,
                        numero_operadores INTEGER,
                        hora_inicio TEXT,
                        hora_fim TEXT,
                        quantidade INTEGER DEFAULT 0,
                        pecas_mortas INTEGER DEFAULT 0,
                        quantidade_total INTEGER DEFAULT 0,
                        created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_timestamp
                    ON production_entries(timestamp DESC)
                """)
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_source_hash
                    ON production_entries(source_hash)
                """)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS painting_entries (
                        id BIGSERIAL PRIMARY KEY,
                        schema_version TEXT,
                        timestamp TIMESTAMPTZ,
                        cliente TEXT,
                        display TEXT,
                        numero_display TEXT,
                        codigo_pintura TEXT,
                        maquinario TEXT,
                        processo TEXT,
                        data_producao TEXT,
                        hora_lancamento TEXT,
                        quantidade INTEGER DEFAULT 0,
                        quantidade_total INTEGER DEFAULT 0,
                        source_hash TEXT UNIQUE,
                        created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_painting_timestamp
                    ON painting_entries(timestamp DESC)
                """)
            conn.commit()

    def _entry_values(self, data: Dict[str, Any]) -> tuple:
        return (
            data.get("schema_version"),
            data.get("timestamp"),
            data.get("cliente"),
            data.get("display"),
            data.get("numero_display"),
            data.get("maquinario"),
            data.get("processo"),
            data.get("data_producao"),
            data.get("operadores"),
            data.get("numero_operadores"),
            data.get("hora_inicio"),
            data.get("hora_fim"),
            data.get("quantidade", 0),
            data.get("pecas_mortas", 0),
            data.get("quantidade_total", 0),
            data.get("source_hash"),
            data.get("import_key"),
        )

    def save_entry(self, data: Dict[str, Any]) -> int:
        """Salva novo registro de producao."""
        columns = """
            schema_version, timestamp, cliente, display, numero_display,
            maquinario, processo, data_producao, operadores, numero_operadores,
            hora_inicio, hora_fim, quantidade, pecas_mortas,
            quantidade_total, source_hash, import_key
        """
        placeholders = ", ".join([self.placeholder] * 17)

        with self.get_conn() as conn:
            if self.backend == "postgres":
                with conn.cursor() as cursor:
                    cursor.execute(
                        f"""
                        INSERT INTO production_entries ({columns})
                        VALUES ({placeholders})
                        RETURNING id
                        """,
                        self._entry_values(data),
                    )
                    entry_id = cursor.fetchone()["id"]
                conn.commit()
                return entry_id

            cursor = conn.execute(
                f"""
                INSERT INTO production_entries ({columns})
                VALUES ({placeholders})
                """,
                self._entry_values(data),
            )
            conn.commit()
            return cursor.lastrowid

    def save_painting_entry(self, data: Dict[str, Any]) -> int:
        """Salva um novo lancamento de pintura sem misturar com a producao."""
        columns = """
            schema_version, timestamp, cliente, display, numero_display,
            codigo_pintura, maquinario, processo, data_producao,
            hora_lancamento, quantidade, quantidade_total, source_hash
        """
        values = (
            data.get("schema_version"), data.get("timestamp"), data.get("cliente"),
            data.get("display"), data.get("numero_display"), data.get("codigo_pintura"),
            data.get("maquinario"), data.get("processo"), data.get("data_producao"),
            data.get("hora_lancamento"), data.get("quantidade", 0),
            data.get("quantidade_total", 0), data.get("source_hash"),
        )
        placeholders = ", ".join([self.placeholder] * len(values))

        with self.get_conn() as conn:
            if self.backend == "postgres":
                with conn.cursor() as cursor:
                    cursor.execute(
                        f"INSERT INTO painting_entries ({columns}) VALUES ({placeholders}) RETURNING id",
                        values,
                    )
                    entry_id = cursor.fetchone()["id"]
                conn.commit()
                return entry_id

            cursor = conn.execute(
                f"INSERT INTO painting_entries ({columns}) VALUES ({placeholders})", values,
            )
            conn.commit()
            return cursor.lastrowid

    def get_all_entries(self) -> List[Dict]:
        """Retorna todos os registros ordenados por timestamp."""
        with self.get_conn() as conn:
            cursor = conn.execute("""
                SELECT * FROM production_entries
                ORDER BY timestamp DESC, id DESC
            """)
            return [dict(row) for row in cursor.fetchall()]

    def get_entries_paginated(self, limit: int = 50, offset: int = 0) -> Tuple[List[Dict], int]:
        """Retorna registros com paginacao."""
        with self.get_conn() as conn:
            cursor = conn.execute("SELECT COUNT(*) as count FROM production_entries")
            total = dict(cursor.fetchone())["count"]

            cursor = conn.execute(
                f"""
                SELECT * FROM production_entries
                ORDER BY timestamp DESC, id DESC
                LIMIT {self.placeholder} OFFSET {self.placeholder}
                """,
                (limit, offset),
            )
            rows = [dict(row) for row in cursor.fetchall()]

        return rows, total

    def get_entry_by_id(self, entry_id: int) -> Optional[Dict]:
        """Retorna um registro especifico."""
        with self.get_conn() as conn:
            cursor = conn.execute(
                f"SELECT * FROM production_entries WHERE id = {self.placeholder}",
                (entry_id,),
            )
            row = cursor.fetchone()
            return dict(row) if row else None

    def update_entry(self, entry_id: int, data: Dict[str, Any]) -> bool:
        """Atualiza um registro existente."""
        ph = self.placeholder
        with self.get_conn() as conn:
            cursor = conn.execute(
                f"""
                UPDATE production_entries SET
                    cliente = {ph}, display = {ph}, numero_display = {ph},
                    maquinario = {ph}, processo = {ph}, data_producao = {ph},
                    operadores = {ph}, numero_operadores = {ph},
                    hora_inicio = {ph}, hora_fim = {ph},
                    quantidade = {ph}, pecas_mortas = {ph}, quantidade_total = {ph},
                    source_hash = {ph}
                WHERE id = {ph}
                """,
                (
                    data.get("cliente"),
                    data.get("display"),
                    data.get("numero_display"),
                    data.get("maquinario"),
                    data.get("processo"),
                    data.get("data_producao"),
                    data.get("operadores"),
                    data.get("numero_operadores"),
                    data.get("hora_inicio"),
                    data.get("hora_fim"),
                    data.get("quantidade"),
                    data.get("pecas_mortas"),
                    data.get("quantidade_total"),
                    data.get("source_hash"),
                    entry_id,
                ),
            )
            conn.commit()
            return cursor.rowcount > 0

    def delete_entry(self, entry_id: int) -> bool:
        """Deleta um registro."""
        with self.get_conn() as conn:
            cursor = conn.execute(
                f"DELETE FROM production_entries WHERE id = {self.placeholder}",
                (entry_id,),
            )
            conn.commit()
            return cursor.rowcount > 0

    def search_entries(self, query: str) -> List[Dict]:
        """Busca registros por cliente, display ou processo."""
        search_pattern = f"%{query}%"
        with self.get_conn() as conn:
            cursor = conn.execute(
                f"""
                SELECT * FROM production_entries
                WHERE cliente LIKE {self.placeholder}
                   OR display LIKE {self.placeholder}
                   OR processo LIKE {self.placeholder}
                ORDER BY timestamp DESC
                """,
                (search_pattern, search_pattern, search_pattern),
            )
            return [dict(row) for row in cursor.fetchall()]

    def get_entries_by_date_range(self, start_date: str, end_date: str) -> List[Dict]:
        """Retorna registros em intervalo de datas."""
        with self.get_conn() as conn:
            cursor = conn.execute(
                f"""
                SELECT * FROM production_entries
                WHERE data_producao BETWEEN {self.placeholder} AND {self.placeholder}
                ORDER BY timestamp DESC
                """,
                (start_date, end_date),
            )
            return [dict(row) for row in cursor.fetchall()]


def _normalize_text(value) -> str:
    """Normaliza texto."""
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    return str(value).strip()


def _normalize_operadores(value) -> str:
    """Normaliza lista de operadores para texto legivel."""
    if isinstance(value, (list, tuple, set)):
        return "; ".join(_normalize_text(item) for item in value if _normalize_text(item))
    return _normalize_text(value)


def _normalize_int(value):
    """Normaliza numero."""
    text = _normalize_text(value)
    if not text:
        return None
    try:
        return int(text)
    except ValueError:
        return None


def _build_source_hash(payload: dict) -> str:
    """Cria hash unico para evitar duplicatas."""
    ordered_keys = [
        "schema_version",
        "timestamp",
        "cliente",
        "display",
        "numero_display",
        "maquinario",
        "processo",
        "data_producao",
        "operadores",
        "numero_operadores",
        "hora_inicio",
        "hora_fim",
        "quantidade",
        "pecas_mortas",
        "quantidade_total",
    ]
    normalized_values = []
    for key in ordered_keys:
        value = payload.get(key, "")
        if key == "timestamp" and isinstance(value, datetime):
            normalized_values.append(value.isoformat())
        else:
            normalized_values.append(_normalize_text(value))
    raw = "||".join(normalized_values)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def build_entry_payload_from_streamlit(payload: dict, schema_version: str) -> dict:
    """Constroi payload normalizado a partir de dados do Streamlit."""
    timestamp = datetime.now()

    entry_payload = {
        "schema_version": schema_version,
        "timestamp": timestamp.isoformat(),
        "cliente": _normalize_text(payload.get("cliente")),
        "display": _normalize_text(payload.get("acabado")),
        "numero_display": _normalize_text(payload.get("numero_display")),
        "maquinario": _normalize_text(payload.get("ferramental")),
        "processo": _normalize_text(payload.get("processo")),
        "data_producao": _normalize_text(payload.get("data_producao")),
        "operadores": _normalize_operadores(payload.get("operadores")),
        "numero_operadores": _normalize_int(payload.get("numero_operadores")) or 0,
        "hora_inicio": _normalize_text(payload.get("hora_iniciada")),
        "hora_fim": _normalize_text(payload.get("hora_finalizada")),
        "quantidade": _normalize_int(payload.get("quantidade_produzida")) or 0,
        "pecas_mortas": _normalize_int(payload.get("pecas_mortas")) or 0,
        "quantidade_total": _normalize_int(payload.get("quantidade_total")) or 0,
    }
    entry_payload["source_hash"] = _build_source_hash(entry_payload)
    return entry_payload


def build_entry_update_payload_from_streamlit(
    payload: dict,
    existing_entry: dict,
    schema_version: str,
) -> dict:
    """Constroi payload para ajuste preservando dados de controle do registro."""
    entry_payload = build_entry_payload_from_streamlit(payload, schema_version)
    entry_payload["schema_version"] = existing_entry.get("schema_version") or schema_version
    entry_payload["timestamp"] = existing_entry.get("timestamp") or entry_payload["timestamp"]
    entry_payload["source_hash"] = _build_source_hash(entry_payload)
    return entry_payload


_db_instance = None


def get_db() -> ProductionDB:
    """Retorna instancia global do banco de dados."""
    global _db_instance
    if _db_instance is None:
        _db_instance = ProductionDB()
    return _db_instance


def reset_db_instance() -> None:
    """Limpa singleton para testes ou troca de configuracao."""
    global _db_instance
    _db_instance = None
