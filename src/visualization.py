from __future__ import annotations

import pandas as pd
import plotly.express as px
from rapidfuzz import fuzz

from src.data_loader import load_dataset
from src.utils import normalize_text


def _mob_portfolio_with_sales() -> pd.DataFrame:
    mob_df = load_dataset("mob_portfolio").copy()
    mob_df["Req_Qty_Total"] = pd.to_numeric(mob_df.get("Req_Qty_Total", 0), errors="coerce").fillna(0)
    return mob_df


def _external_products_with_status() -> pd.DataFrame:
    external_df = load_dataset("raw_external_products").copy()
    substitute_df = load_dataset("substitute_database").copy()
    if external_df.empty:
        external_df["has_substitute"] = pd.Series(dtype=bool)
        return external_df

    linked_ids = set(substitute_df.get("external_id", pd.Series(dtype=str)).fillna("").astype(str).str.strip())
    linked_ids.discard("")
    external_df["external_id"] = external_df["external_id"].fillna("").astype(str).str.strip()
    external_df["has_substitute"] = external_df["external_id"].isin(linked_ids)
    return external_df


def _products_without_substitute_with_qty() -> pd.DataFrame:
    gap_df = _external_products_with_status().copy()
    if "has_substitute" in gap_df.columns:
        gap_df = gap_df[~gap_df["has_substitute"]].copy()
    gap_df["qty_requested"] = pd.to_numeric(gap_df.get("qty_requested", 0), errors="coerce").fillna(0)
    return gap_df


def _filter_category(df: pd.DataFrame, column: str, category: str | None) -> pd.DataFrame:
    if df.empty or not category or category == "All":
        return df
    return df[df[column].fillna("Unknown") == category]


def _detect_product_families(
    df: pd.DataFrame,
    *,
    name_column: str,
    category_column: str,
    value_column: str,
    threshold: int = 88,
) -> pd.DataFrame:
    if df.empty:
        output = df.copy()
        output["product_family"] = ""
        return output

    working = df.copy()
    working["normalized_name"] = working[name_column].fillna("").map(normalize_text)

    unique_names = (
        working.groupby([category_column, "normalized_name", name_column], dropna=False)[value_column]
        .sum()
        .reset_index()
        .sort_values([category_column, value_column], ascending=[True, False])
    )

    family_rows: list[dict[str, str]] = []
    for category, group in unique_names.groupby(category_column, dropna=False):
        families: list[dict[str, str]] = []
        for _, row in group.iterrows():
            normalized_name = row["normalized_name"]
            display_name = row[name_column] if str(row[name_column]).strip() else "Unnamed product"
            assigned_family = None
            best_score = -1

            for family in families:
                score = fuzz.token_set_ratio(normalized_name, family["normalized_name"])
                contains_match = normalized_name in family["normalized_name"] or family["normalized_name"] in normalized_name
                if score > best_score and (score >= threshold or (contains_match and score >= 72)):
                    best_score = score
                    assigned_family = family["family_name"]

            if assigned_family is None:
                assigned_family = display_name
                families.append({"family_name": assigned_family, "normalized_name": normalized_name})

            family_rows.append(
                {
                    category_column: category,
                    "normalized_name": normalized_name,
                    "product_family": assigned_family,
                }
            )

    family_map = pd.DataFrame(family_rows).drop_duplicates([category_column, "normalized_name"])
    return working.merge(family_map, on=[category_column, "normalized_name"], how="left")


def data_quality_metrics() -> dict[str, float]:
    raw_df = load_dataset("raw_external_products")
    return {
        "Total raw products": float(len(raw_df)),
        "Unique external IDs": float(raw_df["external_id"].nunique(dropna=True)) if not raw_df.empty else 0,
    }


def substitution_metrics() -> dict[str, float]:
    external_df = _external_products_with_status()
    total = external_df["external_id"].nunique() if not external_df.empty else 0
    linked = int(external_df["has_substitute"].sum()) if "has_substitute" in external_df.columns else 0
    coverage = round((linked / total) * 100, 1) if total else 0
    return {
        "External products": float(total),
        "Linked substitutes": float(linked),
        "Coverage rate %": coverage,
    }


def mob_sales_metrics() -> dict[str, float]:
    mob_df = _mob_portfolio_with_sales()
    family_df = _detect_product_families(
        mob_df,
        name_column="MOB_Name",
        category_column="Kategorie",
        value_column="Req_Qty_Total",
    )
    return {
        "Portfolio products": float(mob_df["MOB_ID"].nunique()) if not mob_df.empty else 0,
        "Detected families": float(family_df["product_family"].nunique()) if "product_family" in family_df.columns else 0,
        "Products with sales": float(mob_df[mob_df["Req_Qty_Total"] > 0]["MOB_ID"].nunique()) if not mob_df.empty else 0,
        "Total sales qty": float(mob_df["Req_Qty_Total"].sum()) if not mob_df.empty else 0,
    }


def gap_metrics() -> dict[str, float]:
    gap_df = _products_without_substitute_with_qty()
    family_df = _detect_product_families(
        gap_df,
        name_column="external_name",
        category_column="category",
        value_column="qty_requested",
    )
    return {
        "Products without substitute": float(gap_df["external_id"].nunique()) if not gap_df.empty else 0,
        "Gap families": float(family_df["product_family"].nunique()) if "product_family" in family_df.columns else 0,
        "Gap qty requested": float(gap_df["qty_requested"].sum()) if not gap_df.empty else 0,
    }


def mob_sales_by_category_chart(selected_category: str | None = None):
    mob_df = _mob_portfolio_with_sales()
    if mob_df.empty:
        return None
    summary = mob_df.groupby("Kategorie", dropna=False)["Req_Qty_Total"].sum().reset_index().sort_values("Req_Qty_Total", ascending=False)
    summary["Kategorie"] = summary["Kategorie"].fillna("Unknown")
    summary["selected"] = summary["Kategorie"].eq(selected_category)
    fig = px.bar(
        summary,
        x="Kategorie",
        y="Req_Qty_Total",
        color="selected",
        color_discrete_map={True: "#0f766e", False: "#cbd5e1"},
        title="MOB Sales by Category",
    )
    fig.update_layout(showlegend=False)
    return fig


def top_mob_families_chart(limit: int = 12, category: str | None = None):
    mob_df = _detect_product_families(
        _mob_portfolio_with_sales(),
        name_column="MOB_Name",
        category_column="Kategorie",
        value_column="Req_Qty_Total",
    )
    if mob_df.empty:
        return None
    mob_df["Kategorie"] = mob_df["Kategorie"].fillna("Unknown")
    mob_df = _filter_category(mob_df, "Kategorie", category)
    if mob_df.empty:
        return None
    summary = mob_df.groupby("product_family", dropna=False)["Req_Qty_Total"].sum().reset_index().sort_values("Req_Qty_Total", ascending=False).head(limit)
    title_suffix = f" in {category}" if category and category != "All" else ""
    return px.bar(summary.sort_values("Req_Qty_Total", ascending=True), x="Req_Qty_Total", y="product_family", orientation="h", title=f"Top {limit} MOB Product Families{title_suffix}")


def top_mob_products_chart(limit: int = 12, category: str | None = None):
    mob_df = _mob_portfolio_with_sales()
    if mob_df.empty:
        return None
    mob_df["Kategorie"] = mob_df["Kategorie"].fillna("Unknown")
    mob_df = _filter_category(mob_df, "Kategorie", category)
    if mob_df.empty:
        return None
    summary = mob_df.copy()
    summary["normalized_name"] = summary["MOB_Name"].fillna("").map(normalize_text)
    summary["normalized_variant"] = summary["Größe/Variante"].fillna("").map(normalize_text)
    summary["display_variant"] = summary["Größe/Variante"].fillna("").replace("", "No size / variant")
    summary = (
        summary.groupby(
            ["Kategorie", "normalized_name", "normalized_variant", "MOB_Name", "display_variant"],
            dropna=False,
        )
        .agg(
            Req_Qty_Total=("Req_Qty_Total", "sum"),
            mob_id_count=("MOB_ID", "nunique"),
            sample_mob_id=("MOB_ID", "first"),
        )
        .reset_index()
    )
    summary["product_label"] = (
        summary["MOB_Name"].fillna("").str.slice(0, 34)
        + summary["MOB_Name"].fillna("").map(lambda value: "..." if len(str(value)) > 34 else "")
        + " | "
        + summary["sample_mob_id"].astype(str)
    )
    summary["full_product_label"] = (
        summary["MOB_Name"].fillna("")
        + " | "
        + summary["display_variant"]
        + " | IDs: "
        + summary["sample_mob_id"].astype(str)
        + summary["mob_id_count"].map(lambda count: f" (+{count - 1} more IDs)" if count > 1 else "")
    )
    summary = summary.sort_values("Req_Qty_Total", ascending=False).head(limit)
    fig = px.bar(
        summary.sort_values("Req_Qty_Total", ascending=True),
        x="Req_Qty_Total",
        y="product_label",
        orientation="h",
        hover_data={
            "MOB_Name": True,
            "display_variant": True,
            "sample_mob_id": True,
            "mob_id_count": True,
            "Req_Qty_Total": ":,.0f",
            "product_label": False,
            "full_product_label": False,
        },
        title=f"Top {limit} MOB Products{f' in {category}' if category and category != 'All' else ''}",
    )
    fig.update_layout(
        yaxis={"automargin": True},
        margin={"l": 40, "r": 20, "t": 60, "b": 40},
    )
    return fig


def products_without_substitute_by_category_chart(selected_category: str | None = None):
    gap_df = _products_without_substitute_with_qty()
    if gap_df.empty:
        return None
    summary = gap_df.groupby("category", dropna=False)["qty_requested"].sum().reset_index().sort_values("qty_requested", ascending=False)
    summary["category"] = summary["category"].fillna("Unknown")
    summary["selected"] = summary["category"].eq(selected_category)
    fig = px.bar(
        summary,
        x="category",
        y="qty_requested",
        color="selected",
        color_discrete_map={True: "#b45309", False: "#fde68a"},
        title="Products Without Substitute by Category",
    )
    fig.update_layout(showlegend=False)
    return fig


def top_products_without_substitute_families_chart(limit: int = 12, category: str | None = None):
    gap_df = _detect_product_families(
        _products_without_substitute_with_qty(),
        name_column="external_name",
        category_column="category",
        value_column="qty_requested",
    )
    if gap_df.empty:
        return None
    gap_df["category"] = gap_df["category"].fillna("Unknown")
    gap_df = _filter_category(gap_df, "category", category)
    if gap_df.empty:
        return None
    summary = gap_df.groupby("product_family", dropna=False)["qty_requested"].sum().reset_index().sort_values("qty_requested", ascending=False).head(limit)
    title_suffix = f" in {category}" if category and category != "All" else ""
    return px.bar(summary.sort_values("qty_requested", ascending=True), x="qty_requested", y="product_family", orientation="h", title=f"Top {limit} Products Without Substitute{title_suffix}")


def mob_category_options() -> list[str]:
    mob_df = _mob_portfolio_with_sales()
    categories = sorted({str(value).strip() or "Unknown" for value in mob_df.get("Kategorie", pd.Series(dtype=str)).fillna("Unknown")})
    return ["All", *categories]


def gap_category_options() -> list[str]:
    gap_df = _products_without_substitute_with_qty()
    categories = sorted({str(value).strip() or "Unknown" for value in gap_df.get("category", pd.Series(dtype=str)).fillna("Unknown")})
    return ["All", *categories]
