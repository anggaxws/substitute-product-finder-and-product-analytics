from __future__ import annotations

from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "substitution_tool.db"

DATASETS = {
    "raw_external_products": {
        "table": "external_products",
        "columns": [
            "external_id",
            "duplicate_detection",
            "external_name",
            "manufacturer",
            "category",
            "last_update",
            "qty_requested",
            "created_date",
            "source_file",
            "import_date",
        ],
        "required_import_columns": ["external_id", "external_name"],
        "unique_keys": ["external_id"],
    },
    "mob_portfolio": {
        "table": "mob_portfolio",
        "columns": [
            "MOB_ID",
            "MOB_Name",
            "Kategorie",
            "Größe/Variante",
            "Aktiv (Y/N)",
            "Last_Updated",
            "Req_Qty_Total",
        ],
        "required_import_columns": ["MOB_ID", "MOB_Name"],
        "unique_keys": ["MOB_ID"],
    },
    "substitute_database": {
        "table": "substitute_database",
        "columns": [
            "external_id",
            "mob_id",
            "source_file",
            "import_date",
        ],
        "required_import_columns": ["external_id", "mob_id"],
        "unique_keys": ["external_id", "mob_id"],
    },
}


def empty_frame(dataset_name: str) -> pd.DataFrame:
    return pd.DataFrame(columns=DATASETS[dataset_name]["columns"])


def ensure_data_files() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
