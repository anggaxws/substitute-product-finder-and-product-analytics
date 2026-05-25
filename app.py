from __future__ import annotations

import streamlit as st

from src.substitution import connected_substitutions_view, lookup_substitutions
from src.visualization import (
    gap_metrics,
    mob_sales_by_category_chart,
    mob_sales_metrics,
    products_without_substitute_by_category_chart,
    substitution_metrics,
    top_mob_families_chart,
    top_products_without_substitute_families_chart,
)

st.set_page_config(page_title="Dashboard", page_icon="ST", layout="wide")

st.title("Dashboard")
st.caption("Search an external product on the left and review the portfolio substitute on the right.")

lookup_df = lookup_substitutions("")

with st.container(border=True):
    left_col, right_col = st.columns([1, 1.2], gap="large")

    with left_col:
        st.subheader("External Product Input")
        external_id_query = st.text_input("External ID")
        external_name_query = st.text_input("External Product Name")

        filtered_lookup = lookup_df.copy()
        if external_id_query:
            filtered_lookup = filtered_lookup[
                filtered_lookup["external_id"].fillna("").astype(str).str.contains(external_id_query, case=False, regex=False)
            ]
        if external_name_query:
            filtered_lookup = filtered_lookup[
                filtered_lookup["external_name"].fillna("").astype(str).str.contains(external_name_query, case=False, regex=False)
            ]

        if external_id_query or external_name_query:
            st.caption(f"Matches found: {len(filtered_lookup)}")
        else:
            st.info("Enter an external ID or external product name to look up a substitute.")

    with right_col:
        st.subheader("Substitute Result")
        if not (external_id_query or external_name_query):
            st.info("The selected substitute result will appear here.")
        elif filtered_lookup.empty:
            st.warning("No matching external product was found.")
        else:
            selected_row = filtered_lookup.iloc[0]

            result_top_left, result_top_right = st.columns(2)
            result_top_left.text_input("Matched External ID", value=str(selected_row.get("external_id", "")), disabled=True)
            result_top_right.text_input("Matched External Name", value=str(selected_row.get("external_name", "")), disabled=True)

            result_mid_left, result_mid_right = st.columns(2)
            result_mid_left.text_input("External Category", value=str(selected_row.get("category", "")), disabled=True)
            result_mid_right.text_input("Qty Requested", value=str(selected_row.get("qty_requested", "")), disabled=True)

            st.markdown("**Portfolio Substitute**")
            substitute_left, substitute_right = st.columns(2)
            substitute_left.text_input("MOB ID", value=str(selected_row.get("mob_id", "")), disabled=True)
            substitute_right.text_input("MOB Name", value=str(selected_row.get("mob_name", "")), disabled=True)

            detail_left, detail_right = st.columns(2)
            detail_left.text_input("Portfolio Category", value=str(selected_row.get("mob_category", "")), disabled=True)
            detail_right.text_input("Size / Variant", value=str(selected_row.get("mob_size_variant", "")), disabled=True)

    if external_id_query or external_name_query:
        st.markdown("**Matching Rows**")
        result_columns = [
            "external_id",
            "external_name",
            "category",
            "qty_requested",
            "mob_id",
            "mob_name",
            "mob_category",
        ]
        available_columns = [column for column in result_columns if column in filtered_lookup.columns]
        st.dataframe(filtered_lookup[available_columns], use_container_width=True, height=220)

st.subheader("Overview")
sub_metrics = substitution_metrics()
sales_metrics = mob_sales_metrics()
gap_summary = gap_metrics()
overview_metrics = {
    "External products": int(sub_metrics["External products"]),
    "Linked substitutes": int(sub_metrics["Linked substitutes"]),
    "Coverage rate %": sub_metrics["Coverage rate %"],
    "Portfolio products": int(sales_metrics["Portfolio products"]),
    "Detected families": int(sales_metrics["Detected families"]),
    "Total sales qty": int(sales_metrics["Total sales qty"]),
    "Gap families": int(gap_summary["Gap families"]),
    "Gap qty requested": int(gap_summary["Gap qty requested"]),
}
metric_columns = st.columns(len(overview_metrics))
for column, (label, value) in zip(metric_columns, overview_metrics.items()):
    column.metric(label, value)

connected_subs_df = connected_substitutions_view()

chart_col1, chart_col2 = st.columns(2)
sales_by_category_fig = mob_sales_by_category_chart()
if sales_by_category_fig is not None:
    chart_col1.plotly_chart(sales_by_category_fig, use_container_width=True)

top_families_fig = top_mob_families_chart()
if top_families_fig is not None:
    chart_col2.plotly_chart(top_families_fig, use_container_width=True)

chart_col3, chart_col4 = st.columns(2)
gap_by_category_fig = products_without_substitute_by_category_chart()
if gap_by_category_fig is not None:
    chart_col3.plotly_chart(gap_by_category_fig, use_container_width=True)

top_gap_families_fig = top_products_without_substitute_families_chart()
if top_gap_families_fig is not None:
    chart_col4.plotly_chart(top_gap_families_fig, use_container_width=True)

st.subheader("Connected Substitutions")
connected_columns = [
    "external_id",
    "external_name",
    "category",
    "mob_id",
    "mob_name",
    "mob_category",
    "mob_size_variant",
]
available_connected_columns = [column for column in connected_columns if column in connected_subs_df.columns]
st.dataframe(connected_subs_df[available_connected_columns], use_container_width=True, height=320)
