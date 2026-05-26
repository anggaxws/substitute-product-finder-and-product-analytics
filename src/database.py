from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd

from src.config import DATASETS, DB_PATH, DATA_DIR, ensure_data_files


SCHEMA_VERSION = "1"


def _quote_identifier(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def _connect() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=OFF")
    return conn


def _normalize_dataset(dataset_name: str, df: pd.DataFrame) -> pd.DataFrame:
    output = df.copy()
    spec = DATASETS[dataset_name]
    for column in spec["columns"]:
        if column not in output.columns:
            output[column] = ""
    return output[spec["columns"]].fillna("").astype(str)


def _create_schema(conn: sqlite3.Connection) -> None:
    conn.execute('CREATE TABLE IF NOT EXISTS app_metadata ("key" TEXT PRIMARY KEY, "value" TEXT NOT NULL)')

    for spec in DATASETS.values():
        column_defs = ", ".join(f'{_quote_identifier(column)} TEXT' for column in spec["columns"])
        conn.execute(f'CREATE TABLE IF NOT EXISTS {_quote_identifier(spec["table"])} ({column_defs})')

        unique_keys = spec.get("unique_keys", [])
        if unique_keys:
            index_name = f'idx_{spec["table"]}_unique'
            unique_columns = ", ".join(_quote_identifier(column) for column in unique_keys)
            conn.execute(
                f'CREATE UNIQUE INDEX IF NOT EXISTS {_quote_identifier(index_name)} '
                f'ON {_quote_identifier(spec["table"])} ({unique_columns})'
            )

    metadata_row = conn.execute('SELECT "value" FROM app_metadata WHERE "key" = "schema_version"').fetchone()
    if metadata_row is None:
        conn.execute(
            'INSERT INTO app_metadata ("key", "value") VALUES (?, ?)',
            ("schema_version", SCHEMA_VERSION),
        )
    conn.commit()


def _dataset_row_count(conn: sqlite3.Connection, dataset_name: str) -> int:
    table_name = DATASETS[dataset_name]["table"]
    query = f'SELECT COUNT(*) FROM {_quote_identifier(table_name)}'
    return int(conn.execute(query).fetchone()[0])


def _write_dataset(conn: sqlite3.Connection, dataset_name: str, df: pd.DataFrame) -> None:
    spec = DATASETS[dataset_name]
    normalized = _normalize_dataset(dataset_name, df)
    table_name = _quote_identifier(spec["table"])
    with conn:
        conn.execute(f"DELETE FROM {table_name}")
        if not normalized.empty:
            normalized.to_sql(spec["table"], conn, if_exists="append", index=False)


def ensure_database() -> None:
    ensure_data_files()
    with _connect() as conn:
        _create_schema(conn)


def load_dataset_from_db(dataset_name: str) -> pd.DataFrame:
    ensure_database()
    spec = DATASETS[dataset_name]
    with _connect() as conn:
        df = pd.read_sql_query(f'SELECT * FROM {_quote_identifier(spec["table"])}', conn)
    return _normalize_dataset(dataset_name, df)


def save_dataset_to_db(dataset_name: str, df: pd.DataFrame) -> None:
    ensure_database()
    with _connect() as conn:
        _write_dataset(conn, dataset_name, df)


def database_status() -> dict[str, int | str]:
    ensure_database()
    with _connect() as conn:
        metadata_row = conn.execute('SELECT "value" FROM app_metadata WHERE "key" = "schema_version"').fetchone()
        return {
            "path": str(Path(DB_PATH)),
            "schema_version": metadata_row[0] if metadata_row else "",
            "external_products": _dataset_row_count(conn, "raw_external_products"),
            "mob_portfolio": _dataset_row_count(conn, "mob_portfolio"),
            "substitute_database": _dataset_row_count(conn, "substitute_database"),
        }
