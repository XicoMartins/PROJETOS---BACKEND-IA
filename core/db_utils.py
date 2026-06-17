"""
Database utilities - Implementação sem Django usando SQLite puro
Compatível com Streamlit Cloud
"""

import sqlite3
import hashlib
from datetime import datetime
from pathlib import Path
from contextlib import contextmanager
from typing import List, Dict, Any, Optional, Tuple


class ProductionDB:
    """Gerenciador de banco SQLite sem dependência de Django"""

    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            # Detecta se está em Streamlit Cloud ou local
            if Path("/app").exists():
                # Streamlit Cloud - usar /tmp (volátil)
                db_path = "/tmp/production.db"
            else:
                # Local - usar home directory
                db_path = str(Path.home() / ".mtech" / "production.db")

        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    @contextmanager
    def get_conn(self):
        """Context manager para conexões seguras"""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def _init_schema(self):
        """Cria tabelas se não existirem"""
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
            conn.commit()

    def save_entry(self, data: Dict[str, Any]) -> int:
        """Salva novo registro de produção"""
        with self.get_conn() as conn:
            cursor = conn.execute("""
                INSERT INTO production_entries (
                    schema_version, timestamp, cliente, display, numero_display,
                    maquinario, processo, data_producao, operadores, numero_operadores,
                    hora_inicio, hora_fim, quantidade, pecas_mortas,
                    quantidade_total, source_hash, import_key
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                data.get('schema_version'),
                data.get('timestamp'),
                data.get('cliente'),
                data.get('display'),
                data.get('numero_display'),
                data.get('maquinario'),
                data.get('processo'),
                data.get('data_producao'),
                data.get('operadores'),
                data.get('numero_operadores'),
                data.get('hora_inicio'),
                data.get('hora_fim'),
                data.get('quantidade', 0),
                data.get('pecas_mortas', 0),
                data.get('quantidade_total', 0),
                data.get('source_hash'),
                data.get('import_key'),
            ))
            conn.commit()
            return cursor.lastrowid

    def get_all_entries(self) -> List[Dict]:
        """Retorna todos os registros ordenados por timestamp"""
        with self.get_conn() as conn:
            cursor = conn.execute("""
                SELECT * FROM production_entries 
                ORDER BY timestamp DESC, id DESC
            """)
            return [dict(row) for row in cursor.fetchall()]

    def get_entries_paginated(self, limit: int = 50, offset: int = 0) -> Tuple[List[Dict], int]:
        """Retorna registros com paginação"""
        with self.get_conn() as conn:
            # Total
            cursor = conn.execute("SELECT COUNT(*) as count FROM production_entries")
            total = cursor.fetchone()['count']

            # Dados
            cursor = conn.execute("""
                SELECT * FROM production_entries 
                ORDER BY timestamp DESC, id DESC
                LIMIT ? OFFSET ?
            """, (limit, offset))
            rows = [dict(row) for row in cursor.fetchall()]

        return rows, total

    def get_entry_by_id(self, entry_id: int) -> Optional[Dict]:
        """Retorna um registro específico"""
        with self.get_conn() as conn:
            cursor = conn.execute(
                "SELECT * FROM production_entries WHERE id = ?",
                (entry_id,)
            )
            row = cursor.fetchone()
            return dict(row) if row else None

    def update_entry(self, entry_id: int, data: Dict[str, Any]) -> bool:
        """Atualiza um registro existente"""
        with self.get_conn() as conn:
            cursor = conn.execute("""
                UPDATE production_entries SET
                    cliente = ?, display = ?, numero_display = ?,
                    maquinario = ?, processo = ?, data_producao = ?,
                    operadores = ?, numero_operadores = ?,
                    hora_inicio = ?, hora_fim = ?,
                    quantidade = ?, pecas_mortas = ?, quantidade_total = ?,
                    source_hash = ?
                WHERE id = ?
            """, (
                data.get('cliente'),
                data.get('display'),
                data.get('numero_display'),
                data.get('maquinario'),
                data.get('processo'),
                data.get('data_producao'),
                data.get('operadores'),
                data.get('numero_operadores'),
                data.get('hora_inicio'),
                data.get('hora_fim'),
                data.get('quantidade'),
                data.get('pecas_mortas'),
                data.get('quantidade_total'),
                data.get('source_hash'),
                entry_id
            ))
            conn.commit()
            return cursor.rowcount > 0

    def delete_entry(self, entry_id: int) -> bool:
        """Deleta um registro"""
        with self.get_conn() as conn:
            cursor = conn.execute(
                "DELETE FROM production_entries WHERE id = ?",
                (entry_id,)
            )
            conn.commit()
            return cursor.rowcount > 0

    def search_entries(self, query: str) -> List[Dict]:
        """Busca registros por cliente, display ou processo"""
        with self.get_conn() as conn:
            search_pattern = f"%{query}%"
            cursor = conn.execute("""
                SELECT * FROM production_entries
                WHERE cliente LIKE ? OR display LIKE ? OR processo LIKE ?
                ORDER BY timestamp DESC
            """, (search_pattern, search_pattern, search_pattern))
            return [dict(row) for row in cursor.fetchall()]

    def get_entries_by_date_range(self, start_date: str, end_date: str) -> List[Dict]:
        """Retorna registros em intervalo de datas"""
        with self.get_conn() as conn:
            cursor = conn.execute("""
                SELECT * FROM production_entries
                WHERE data_producao BETWEEN ? AND ?
                ORDER BY timestamp DESC
            """, (start_date, end_date))
            return [dict(row) for row in cursor.fetchall()]


def _normalize_text(value) -> str:
    """Normaliza texto"""
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    return str(value).strip()


def _normalize_int(value):
    """Normaliza número"""
    text = _normalize_text(value)
    if not text:
        return None
    try:
        return int(text)
    except ValueError:
        return None


def _build_source_hash(payload: dict) -> str:
    """Cria hash único para evitar duplicatas"""
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
    """Constrói payload normalizado a partir de dados do Streamlit"""
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
        "operadores": _normalize_text(payload.get("operadores")),
        "numero_operadores": _normalize_int(payload.get("numero_operadores")) or 0,
        "hora_inicio": _normalize_text(payload.get("hora_iniciada")),
        "hora_fim": _normalize_text(payload.get("hora_finalizada")),
        "quantidade": _normalize_int(payload.get("quantidade_produzida")) or 0,
        "pecas_mortas": _normalize_int(payload.get("pecas_mortas")) or 0,
        "quantidade_total": _normalize_int(payload.get("quantidade_total")) or 0,
    }
    entry_payload["source_hash"] = _build_source_hash(entry_payload)
    return entry_payload


# Singleton global para reutilizar conexão
_db_instance = None


def get_db() -> ProductionDB:
    """Retorna instância global do banco de dados"""
    global _db_instance
    if _db_instance is None:
        _db_instance = ProductionDB()
    return _db_instance
