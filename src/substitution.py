from __future__ import annotations

import pandas as pd

from src.data_loader import load_dataset


def lookup_substitutions(query: str) -> pd.DataFrame:
    raw_df = load_dataset("raw_external_products")
    direct_sub_df = load_dataset("substitute_database")
    mob_df = load_dataset("mob_portfolio").rename(
        columns={
            "MOB_ID": "mob_id",
            "MOB_Name": "mob_name",
            "Kategorie": "mob_category",
            "Größe/Variante": "mob_size_variant",
            "Aktiv (Y/N)": "mob_active_flag",
            "Last_Updated": "mob_last_updated",
            "Req_Qty_Total": "mob_req_qty_total",
        }
    )

    merged = raw_df.merge(direct_sub_df, on="external_id", how="left")
    merged = merged.merge(mob_df, on="mob_id", how="left")
    merged["confidence"] = ""
    merged["note"] = ""

    if not query:
        return merged

    lowered = str(query).lower()
    mask = pd.Series(False, index=merged.index)
    search_columns = [
        "external_id",
        "external_name",
        "category",
        "mob_id",
        "mob_name",
        "mob_category",
        "mob_size_variant",
    ]
    for column in search_columns:
        if column in merged.columns:
            mask = mask | merged[column].fillna("").astype(str).str.lower().str.contains(lowered, regex=False)
    return merged[mask]


def connected_substitutions_view() -> pd.DataFrame:
    lookup_df = lookup_substitutions("")
    output_columns = [
        "external_id",
        "external_name",
        "category",
        "mob_id",
        "mob_name",
        "mob_category",
        "mob_size_variant",
    ]
    available = [column for column in output_columns if column in lookup_df.columns]
    return lookup_df[available].drop_duplicates()
