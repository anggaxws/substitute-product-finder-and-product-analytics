from __future__ import annotations

import pandas as pd

from src.config import DATASETS, empty_frame, ensure_data_files


def load_dataset(dataset_name: str) -> pd.DataFrame:
    ensure_data_files()
    spec = DATASETS[dataset_name]
    path = spec["path"]
    if not path.exists():
        return empty_frame(dataset_name)
    df = pd.read_csv(path)
    for column in spec["columns"]:
        if column not in df.columns:
            df[column] = ""
    return df[spec["columns"]]


def save_dataset(dataset_name: str, df: pd.DataFrame) -> None:
    ensure_data_files()
    spec = DATASETS[dataset_name]
    output = df.copy()
    for column in spec["columns"]:
        if column not in output.columns:
            output[column] = ""
    output = output[spec["columns"]]
    output.to_csv(spec["path"], index=False)
