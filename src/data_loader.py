from __future__ import annotations

import pandas as pd

from src.database import ensure_database, load_dataset_from_db, save_dataset_to_db


def load_dataset(dataset_name: str) -> pd.DataFrame:
    ensure_database()
    return load_dataset_from_db(dataset_name)


def save_dataset(dataset_name: str, df: pd.DataFrame) -> None:
    ensure_database()
    save_dataset_to_db(dataset_name, df)
