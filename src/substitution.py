from __future__ import annotations

import re
import unicodedata

import pandas as pd

from src.data_loader import load_dataset
from src.utils import normalize_text


def _normalize_header(value: object) -> str:
    text = "" if value is None else str(value)
    normalized = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    normalized = re.sub(r"[^a-z0-9]+", "_", normalized.strip().lower())
    return normalized.strip("_")


def _standardize_external_upload(uploaded_df: pd.DataFrame) -> pd.DataFrame:
    header_map = {_normalize_header(column): column for column in uploaded_df.columns}

    def pick_column(*aliases: str) -> str | None:
        for alias in aliases:
            if alias in header_map:
                return header_map[alias]
        return None

    output = pd.DataFrame(index=uploaded_df.index)
    external_id_col = pick_column("external_id", "extern_id", "extern_raw_id", "product_id", "id")
    external_name_col = pick_column("external_name", "extern_name", "product_name", "name", "artikelname", "bezeichnung")
    category_col = pick_column("category", "kategorie")
    qty_col = pick_column("qty_requested", "qty", "quantity", "requested_qty", "menge")

    output["upload_external_id"] = uploaded_df[external_id_col].fillna("").astype(str).str.strip() if external_id_col else ""
    output["upload_external_name"] = uploaded_df[external_name_col].fillna("").astype(str).str.strip() if external_name_col else ""
    output["upload_category"] = uploaded_df[category_col].fillna("").astype(str).str.strip() if category_col else ""
    output["upload_qty_requested"] = uploaded_df[qty_col].fillna("").astype(str).str.strip() if qty_col else ""
    output["normalized_upload_name"] = output["upload_external_name"].map(normalize_text)
    output["upload_row_number"] = range(1, len(output) + 1)
    return output


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


def match_uploaded_external_products(uploaded_df: pd.DataFrame) -> pd.DataFrame:
    upload = _standardize_external_upload(uploaded_df)
    lookup_df = lookup_substitutions("").copy()
    lookup_df["normalized_external_name"] = lookup_df["external_name"].fillna("").map(normalize_text)

    lookup_by_id = {
        str(external_id).strip(): group.copy()
        for external_id, group in lookup_df.groupby(lookup_df["external_id"].fillna("").astype(str).str.strip(), dropna=False)
        if str(external_id).strip()
    }
    lookup_by_name = {
        name: group.copy()
        for name, group in lookup_df.groupby("normalized_external_name", dropna=False)
        if str(name).strip()
    }

    matched_rows: list[dict[str, object]] = []
    for row in upload.to_dict("records"):
        upload_external_id = str(row["upload_external_id"]).strip()
        upload_name = str(row["upload_external_name"]).strip()
        normalized_upload_name = str(row["normalized_upload_name"]).strip()
        row_matches = None

        if upload_external_id and upload_external_id in lookup_by_id:
            row_matches = lookup_by_id[upload_external_id]
            match_method = "external_id"
        elif normalized_upload_name and normalized_upload_name in lookup_by_name:
            row_matches = lookup_by_name[normalized_upload_name]
            match_method = "external_name"
        else:
            match_method = "no_match"

        if row_matches is None or row_matches.empty:
            matched_rows.append(
                {
                    "upload_row_number": row["upload_row_number"],
                    "upload_external_id": upload_external_id,
                    "upload_external_name": upload_name,
                    "upload_category": row["upload_category"],
                    "upload_qty_requested": row["upload_qty_requested"],
                    "matched_external_id": "",
                    "matched_external_name": "",
                    "mob_id": "",
                    "mob_name": "",
                    "mob_category": "",
                    "mob_size_variant": "",
                    "match_method": match_method,
                }
            )
            continue

        for _, match in row_matches.iterrows():
            matched_rows.append(
                {
                    "upload_row_number": row["upload_row_number"],
                    "upload_external_id": upload_external_id,
                    "upload_external_name": upload_name,
                    "upload_category": row["upload_category"],
                    "upload_qty_requested": row["upload_qty_requested"],
                    "matched_external_id": match.get("external_id", ""),
                    "matched_external_name": match.get("external_name", ""),
                    "mob_id": match.get("mob_id", ""),
                    "mob_name": match.get("mob_name", ""),
                    "mob_category": match.get("mob_category", ""),
                    "mob_size_variant": match.get("mob_size_variant", ""),
                    "match_method": match_method,
                }
            )

    return pd.DataFrame(matched_rows)
