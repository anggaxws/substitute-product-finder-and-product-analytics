from __future__ import annotations

from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

DATASETS = {
    "raw_external_products": {
        "path": DATA_DIR / "raw_external_products.csv",
        "columns": [
            "external_id",
            "duplicate_detection",
            "external_name",
            "manufacturer",
            "category",
            "last_update",
            "qty_requested",
            "source_file",
            "import_date",
        ],
        "required_import_columns": ["external_id", "external_name"],
    },
    "mob_portfolio": {
        "path": DATA_DIR / "mob_portfolio.csv",
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
    },
    "products_without_substitute": {
        "path": DATA_DIR / "products_without_substitute.csv",
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
    },
    "substitute_database": {
        "path": DATA_DIR / "substitute_database.csv",
        "columns": [
            "external_id",
            "mob_id",
            "source_file",
            "import_date",
        ],
        "required_import_columns": ["external_id", "mob_id"],
    },
}

def empty_frame(dataset_name: str) -> pd.DataFrame:
    return pd.DataFrame(columns=DATASETS[dataset_name]["columns"])


def ensure_data_files() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    for dataset_name, spec in DATASETS.items():
        path = spec["path"]
        if not path.exists():
            empty_frame(dataset_name).to_csv(path, index=False)
