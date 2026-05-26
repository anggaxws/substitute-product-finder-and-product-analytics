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


def _to_number(value: object) -> float:
    text = "" if value is None else str(value).strip()
    if not text:
        return 0.0
    return float(text.replace(",", "."))


def _format_number(value: float) -> str:
    return str(int(value)) if float(value).is_integer() else f"{value:.2f}".rstrip("0").rstrip(".")


def increment_requested_amounts(updates: list[dict[str, object]]) -> dict[str, object]:
    ensure_database()
    external_df = load_dataset_from_db("raw_external_products")
    mob_df = load_dataset_from_db("mob_portfolio")
    substitute_df = load_dataset_from_db("substitute_database")

    external_df["external_id"] = external_df["external_id"].fillna("").astype(str).str.strip()
    mob_df["MOB_ID"] = mob_df["MOB_ID"].fillna("").astype(str).str.strip()
    substitute_df["external_id"] = substitute_df["external_id"].fillna("").astype(str).str.strip()
    substitute_df["mob_id"] = substitute_df["mob_id"].fillna("").astype(str).str.strip()

    external_index = {external_id: index for index, external_id in external_df["external_id"].items() if external_id}
    mob_index = {mob_id: index for index, mob_id in mob_df["MOB_ID"].items() if mob_id}

    applied_updates: list[dict[str, object]] = []
    missing_external_ids: list[str] = []

    for update in updates:
        external_id = str(update.get("external_id", "")).strip()
        amount = float(update.get("amount", 0))
        if not external_id:
            continue
        if external_id not in external_index:
            missing_external_ids.append(external_id)
            continue

        external_row_index = external_index[external_id]
        previous_external_qty = _to_number(external_df.at[external_row_index, "qty_requested"])
        new_external_qty = previous_external_qty + amount
        external_df.at[external_row_index, "qty_requested"] = _format_number(new_external_qty)

        linked_mob_ids = []
        mob_updates = []
        linked_rows = substitute_df[substitute_df["external_id"] == external_id]
        for mob_id in linked_rows["mob_id"].dropna().astype(str).str.strip().unique():
            if not mob_id or mob_id not in mob_index:
                continue
            mob_row_index = mob_index[mob_id]
            previous_mob_qty = _to_number(mob_df.at[mob_row_index, "Req_Qty_Total"])
            new_mob_qty = previous_mob_qty + amount
            mob_df.at[mob_row_index, "Req_Qty_Total"] = _format_number(new_mob_qty)
            linked_mob_ids.append(mob_id)
            mob_updates.append(
                {
                    "mob_id": mob_id,
                    "previous_qty": _format_number(previous_mob_qty),
                    "new_qty": _format_number(new_mob_qty),
                }
            )

        applied_updates.append(
            {
                "external_id": external_id,
                "amount_added": _format_number(amount),
                "previous_external_qty": _format_number(previous_external_qty),
                "new_external_qty": _format_number(new_external_qty),
                "linked_mob_ids": linked_mob_ids,
                "mob_updates": mob_updates,
            }
        )

    if applied_updates:
        with _connect() as conn:
            _write_dataset(conn, "raw_external_products", external_df)
            _write_dataset(conn, "mob_portfolio", mob_df)

    return {
        "applied_updates": applied_updates,
        "missing_external_ids": missing_external_ids,
    }


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
