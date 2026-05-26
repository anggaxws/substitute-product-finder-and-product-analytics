from __future__ import annotations

import os
import re
import unicodedata
from io import BytesIO
from pathlib import Path

import pandas as pd
import streamlit as st

from src.config import DATASETS
from src.data_loader import load_dataset, save_dataset
from src.database import fetch_audit_log, increment_requested_amounts, log_audit_action
from src.substitution import connected_substitutions_view, lookup_substitutions, match_uploaded_external_products
from src.visualization import (
    gap_category_options,
    gap_metrics,
    mob_category_options,
    mob_sales_by_category_chart,
    mob_sales_metrics,
    products_without_substitute_by_category_chart,
    substitution_metrics,
    top_mob_families_chart,
    top_mob_products_chart,
    top_products_without_substitute_families_chart,
)


ADMIN_PASSWORD = os.getenv("SUBSTITUTION_TOOL_ADMIN_PASSWORD", "admin")


def read_external_upload(uploaded_file) -> pd.DataFrame:
    suffix = Path(uploaded_file.name).suffix.lower()
    file_bytes = uploaded_file.getvalue()
    if suffix == ".csv":
        try:
            return pd.read_csv(BytesIO(file_bytes), sep=None, engine="python")
        except Exception:
            return pd.read_csv(BytesIO(file_bytes), sep=";")
    if suffix in {".xlsx", ".xls", ".xlsm"}:
        return pd.read_excel(BytesIO(file_bytes))
    raise ValueError(f"Unsupported file type: {suffix}")


def normalize_header(value: object) -> str:
    text = "" if value is None else str(value)
    normalized = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    normalized = re.sub(r"[^a-z0-9]+", "_", normalized.strip().lower())
    return normalized.strip("_")


def normalize_editor_output(dataset_name: str, edited_df: pd.DataFrame) -> pd.DataFrame:
    output = edited_df.copy()
    spec = DATASETS[dataset_name]
    for column in spec["columns"]:
        if column not in output.columns:
            output[column] = ""
    output = output[spec["columns"]].fillna("")
    return output.astype(str)


def normalize_uploaded_dataset(dataset_name: str, uploaded_df: pd.DataFrame) -> pd.DataFrame:
    spec = DATASETS[dataset_name]
    uploaded = uploaded_df.copy()
    normalized_column_map = {normalize_header(column): column for column in uploaded.columns}
    matched_columns: dict[str, str] = {}

    for target_column in spec["columns"]:
        normalized_target = normalize_header(target_column)
        if normalized_target in normalized_column_map:
            matched_columns[target_column] = normalized_column_map[normalized_target]

    output = pd.DataFrame(index=uploaded.index)
    for target_column in spec["columns"]:
        source_column = matched_columns.get(target_column)
        if source_column is not None:
            output[target_column] = uploaded[source_column]
        else:
            output[target_column] = ""

    return output.fillna("").astype(str)


def validate_unique_keys(dataset_name: str, df: pd.DataFrame) -> tuple[bool, pd.DataFrame]:
    unique_keys = DATASETS[dataset_name].get("unique_keys", [])
    if not unique_keys:
        return True, pd.DataFrame()

    working = df.copy()
    for column in unique_keys:
        working[column] = working[column].fillna("").astype(str).str.strip()

    # Ignore fully blank key rows that can appear at the bottom of the editor.
    non_blank_mask = working[unique_keys].apply(lambda row: any(value for value in row), axis=1)
    working = working[non_blank_mask].copy()
    if working.empty:
        return True, pd.DataFrame()

    duplicate_mask = working.duplicated(subset=unique_keys, keep=False)
    duplicate_rows = working[duplicate_mask].copy()
    return duplicate_rows.empty, duplicate_rows


def validate_dataset_rules(dataset_name: str, df: pd.DataFrame) -> list[str]:
    errors: list[str] = []

    if dataset_name == "substitute_database":
        working = df.copy().fillna("")
        working["external_id"] = working["external_id"].astype(str).str.strip()
        working["mob_id"] = working["mob_id"].astype(str).str.strip()
        non_blank = working[(working["external_id"] != "") | (working["mob_id"] != "")]

        if ((non_blank["external_id"] == "") | (non_blank["mob_id"] == "")).any():
            errors.append("Every substitute mapping row must include both `external_id` and `mob_id`.")

        external_ids = set(load_dataset("raw_external_products")["external_id"].fillna("").astype(str).str.strip())
        mob_ids = set(load_dataset("mob_portfolio")["MOB_ID"].fillna("").astype(str).str.strip())

        missing_external_ids = sorted({value for value in non_blank["external_id"] if value and value not in external_ids})
        missing_mob_ids = sorted({value for value in non_blank["mob_id"] if value and value not in mob_ids})

        if missing_external_ids:
            errors.append("Unknown external IDs in substitute database: " + ", ".join(missing_external_ids[:10]))
        if missing_mob_ids:
            errors.append("Unknown MOB IDs in substitute database: " + ", ".join(missing_mob_ids[:10]))

    return errors


def parse_requested_amount_updates(raw_text: str) -> tuple[list[dict[str, float | str]], list[str]]:
    updates: list[dict[str, float | str]] = []
    errors: list[str] = []

    for line_number, raw_line in enumerate(raw_text.splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue

        parts = [part.strip() for part in re.split(r"[\t,;|]+", line) if part.strip()]
        if len(parts) != 2:
            errors.append(f"Line {line_number}: expected `external_id, amount`.")
            continue

        external_id, amount_text = parts
        normalized_amount = amount_text.replace(",", ".")
        try:
            amount = float(normalized_amount)
        except ValueError:
            errors.append(f"Line {line_number}: invalid amount `{amount_text}`.")
            continue

        if amount <= 0:
            errors.append(f"Line {line_number}: amount must be greater than 0.")
            continue

        updates.append({"external_id": external_id, "amount": amount})

    return updates, errors


def render_requested_amount_update_result(result: dict[str, object]) -> None:
    applied_updates = result.get("applied_updates", [])
    missing_external_ids = result.get("missing_external_ids", [])

    if applied_updates:
        st.success(f"Applied {len(applied_updates)} requested amount update(s).")
        summary_rows = []
        for item in applied_updates:
            summary_rows.append(
                {
                    "external_id": item["external_id"],
                    "amount_added": item["amount_added"],
                    "previous_external_qty": item["previous_external_qty"],
                    "new_external_qty": item["new_external_qty"],
                    "updated_mob_ids": ", ".join(item["linked_mob_ids"]) if item["linked_mob_ids"] else "No mapped MOB product",
                }
            )
        st.dataframe(pd.DataFrame(summary_rows), use_container_width=True, height=220)

    if missing_external_ids:
        st.warning("Some external IDs were not found: " + ", ".join(missing_external_ids))


st.set_page_config(page_title="Dashboard", page_icon="ST", layout="wide")

st.title("Dashboard")
st.caption("Search an external product on the left and review the portfolio substitute on the right.")

lookup_df = lookup_substitutions("")


def render_substitute_result(row: pd.Series, index: int) -> None:
    st.markdown(f"**Match {index + 1}**")
    result_top_left, result_top_right = st.columns(2)
    result_top_left.text_input(
        "Matched External ID",
        value=str(row.get("external_id", "")),
        disabled=True,
        key=f"matched_external_id_{index}",
    )
    result_top_right.text_input(
        "Matched External Name",
        value=str(row.get("external_name", "")),
        disabled=True,
        key=f"matched_external_name_{index}",
    )

    result_mid_left, result_mid_right = st.columns(2)
    result_mid_left.text_input(
        "External Category",
        value=str(row.get("category", "")),
        disabled=True,
        key=f"matched_external_category_{index}",
    )
    result_mid_right.text_input(
        "Qty Requested",
        value=str(row.get("qty_requested", "")),
        disabled=True,
        key=f"matched_qty_requested_{index}",
    )

    st.markdown("**Portfolio Substitute**")
    substitute_left, substitute_right = st.columns(2)
    substitute_left.text_input("MOB ID", value=str(row.get("mob_id", "")), disabled=True, key=f"matched_mob_id_{index}")
    substitute_right.text_input(
        "MOB Name",
        value=str(row.get("mob_name", "")),
        disabled=True,
        key=f"matched_mob_name_{index}",
    )

    detail_left, detail_right = st.columns(2)
    detail_left.text_input(
        "Portfolio Category",
        value=str(row.get("mob_category", "")),
        disabled=True,
        key=f"matched_mob_category_{index}",
    )
    detail_right.text_input(
        "Size / Variant",
        value=str(row.get("mob_size_variant", "")),
        disabled=True,
        key=f"matched_mob_size_variant_{index}",
    )


def render_category_filter(state_key: str, label: str, categories: list[str]) -> str:
    if state_key not in st.session_state or st.session_state[state_key] not in categories:
        st.session_state[state_key] = "All"

    current_category = str(st.session_state[state_key])
    st.caption(f"{label} Current: `{current_category}`")
    with st.popover("Category Filter", use_container_width=False):
        selected_category = st.selectbox(
            "Choose category",
            categories,
            index=categories.index(current_category),
            key=f"{state_key}_select",
        )
        if selected_category != current_category:
            st.session_state[state_key] = selected_category
            current_category = selected_category
        if st.button("Reset to All", key=f"{state_key}_reset", use_container_width=True):
            st.session_state[state_key] = "All"
            current_category = "All"

    return str(st.session_state[state_key])

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
            st.caption("Scroll to review all matching substitute details.")
            with st.container(height=460, border=True):
                for index, (_, row) in enumerate(filtered_lookup.iterrows()):
                    with st.container(border=True):
                        render_substitute_result(row, index)

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
            "mob_size_variant",
        ]
        available_columns = [column for column in result_columns if column in filtered_lookup.columns]
        st.dataframe(filtered_lookup[available_columns], use_container_width=True, height=220)

with st.expander("Bulk External Product Match", expanded=False):
    st.caption("Upload an external product file and see the matched substitutes below.")
    uploaded_external_file = st.file_uploader(
        "Upload CSV or Excel",
        type=["csv", "xlsx", "xls", "xlsm"],
        key="bulk_external_match",
    )
    if uploaded_external_file is not None:
        try:
            uploaded_external_df = read_external_upload(uploaded_external_file)
            matched_upload_df = match_uploaded_external_products(uploaded_external_df)
            st.success(f"Processed {len(uploaded_external_df)} uploaded row(s).")
            st.dataframe(matched_upload_df, use_container_width=True, height=320)
        except Exception as exc:
            st.error(f"Could not read the uploaded file: {exc}")

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
mob_categories = mob_category_options()
gap_categories = gap_category_options()
if "selected_mob_category" not in st.session_state or st.session_state["selected_mob_category"] not in mob_categories:
    st.session_state["selected_mob_category"] = "All"
if "selected_gap_category" not in st.session_state or st.session_state["selected_gap_category"] not in gap_categories:
    st.session_state["selected_gap_category"] = "All"
selected_mob_category = str(st.session_state["selected_mob_category"])
selected_gap_category = str(st.session_state["selected_gap_category"])

chart_col1, chart_col2 = st.columns(2)
sales_by_category_fig = mob_sales_by_category_chart(selected_mob_category)
if sales_by_category_fig is not None:
    chart_col1.plotly_chart(sales_by_category_fig, use_container_width=True)
chart_col1.write("")
with chart_col1:
    selected_mob_category = render_category_filter(
        "selected_mob_category",
        "MOB category filter.",
        mob_categories,
    )

mob_view_mode = chart_col2.radio(
    "MOB Product View",
    ["Product Families", "Individual Products"],
    horizontal=True,
)
if mob_view_mode == "Product Families":
    top_mob_fig = top_mob_families_chart(category=selected_mob_category)
else:
    top_mob_fig = top_mob_products_chart(category=selected_mob_category)
if top_mob_fig is not None:
    chart_col2.plotly_chart(top_mob_fig, use_container_width=True)
else:
    chart_col2.info("No MOB products found for the selected category.")

chart_col3, chart_col4 = st.columns(2)
gap_by_category_fig = products_without_substitute_by_category_chart(selected_gap_category)
if gap_by_category_fig is not None:
    chart_col3.plotly_chart(gap_by_category_fig, use_container_width=True)
chart_col3.write("")
with chart_col3:
    selected_gap_category = render_category_filter(
        "selected_gap_category",
        "Gap category filter.",
        gap_categories,
    )

top_gap_families_fig = top_products_without_substitute_families_chart(category=selected_gap_category)
if top_gap_families_fig is not None:
    chart_col4.plotly_chart(top_gap_families_fig, use_container_width=True)
else:
    chart_col4.info("No products without substitute found for the selected category.")

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

if "admin_unlocked" not in st.session_state:
    st.session_state.admin_unlocked = False

with st.expander("Admin Panel", expanded=False):
    st.caption("Enter the admin password.")

    if not st.session_state.admin_unlocked:
        admin_password_input = st.text_input("Admin Password", type="password", key="admin_password_input")
        if st.button("Unlock Admin Panel"):
            if admin_password_input == ADMIN_PASSWORD:
                st.session_state.admin_unlocked = True
                st.success("Admin panel unlocked.")
            else:
                st.error("Incorrect admin password.")

    if st.session_state.admin_unlocked:
        st.markdown("**Requested Amount Update**")
        st.caption("Add requested quantity to an external product and automatically add the same quantity to any mapped MOB substitute product.")
        update_tab_single, update_tab_bulk = st.tabs(["Single Update", "Bulk Update"])

        with update_tab_single:
            with st.form("single_requested_amount_update"):
                single_external_id = st.text_input("External ID", key="single_requested_amount_external_id")
                single_amount = st.number_input("Requested Amount to Add", min_value=0.0, step=1.0, key="single_requested_amount_value")
                single_submit = st.form_submit_button("Update Requested Amount")

            if single_submit:
                if not str(single_external_id).strip() or float(single_amount) <= 0:
                    st.error("Enter a valid external ID and an amount greater than 0.")
                else:
                    update_result = increment_requested_amounts(
                        [{"external_id": str(single_external_id).strip(), "amount": float(single_amount)}]
                    )
                    render_requested_amount_update_result(update_result)

        with update_tab_bulk:
            with st.form("bulk_requested_amount_update"):
                bulk_update_text = st.text_area(
                    "Bulk input",
                    height=160,
                    placeholder="168404, 120\n744082, 50\n205961, 300",
                    key="bulk_requested_amount_text",
                )
                bulk_submit = st.form_submit_button("Run Bulk Update")

            if bulk_submit:
                parsed_updates, parse_errors = parse_requested_amount_updates(bulk_update_text)
                if parse_errors:
                    for error in parse_errors:
                        st.error(error)
                elif not parsed_updates:
                    st.error("Enter at least one `external_id, amount` row.")
                else:
                    update_result = increment_requested_amounts(parsed_updates)
                    render_requested_amount_update_result(update_result)

        dataset_tabs = st.tabs(
            [
                "External Products",
                "MOB Portfolio",
                "Substitute Database",
            ]
        )
        dataset_names = [
            "raw_external_products",
            "mob_portfolio",
            "substitute_database",
        ]

        for tab, dataset_name in zip(dataset_tabs, dataset_names):
            with tab:
                current_df = load_dataset(dataset_name).fillna("")
                st.caption(f"Editing `{dataset_name}`")
                edited_df = st.data_editor(
                    current_df,
                    num_rows="dynamic",
                    use_container_width=True,
                    key=f"editor_{dataset_name}",
                    height=360,
                )
                if st.button(f"Save {dataset_name}", key=f"save_{dataset_name}"):
                    normalized_df = normalize_editor_output(dataset_name, edited_df)
                    is_valid, duplicate_rows = validate_unique_keys(dataset_name, normalized_df)
                    validation_errors = validate_dataset_rules(dataset_name, normalized_df)
                    if not is_valid:
                        unique_keys = DATASETS[dataset_name].get("unique_keys", [])
                        st.error(
                            f"Duplicate key detected in {dataset_name}. "
                            f"The columns {', '.join(unique_keys)} must be unique."
                        )
                        st.dataframe(duplicate_rows, use_container_width=True, height=220)
                    elif validation_errors:
                        for error in validation_errors:
                            st.error(error)
                    else:
                        save_dataset(dataset_name, normalized_df)
                        log_audit_action(
                            "admin_save",
                            dataset_name,
                            {"row_count": len(normalized_df)},
                        )
                        st.success(f"Saved changes to {dataset_name}.")

                st.markdown("**Bulk Upload**")
                bulk_file = st.file_uploader(
                    f"Upload CSV or Excel for {dataset_name}",
                    type=["csv", "xlsx", "xls", "xlsm"],
                    key=f"bulk_upload_{dataset_name}",
                )
                upload_mode = st.radio(
                    f"Upload mode for {dataset_name}",
                    ["Append", "Replace"],
                    horizontal=True,
                    key=f"bulk_mode_{dataset_name}",
                )
                if bulk_file is not None and st.button(f"Import into {dataset_name}", key=f"import_{dataset_name}"):
                    try:
                        uploaded_df = read_external_upload(bulk_file)
                        normalized_upload_df = normalize_uploaded_dataset(dataset_name, uploaded_df)
                        combined_df = (
                            pd.concat([current_df, normalized_upload_df], ignore_index=True)
                            if upload_mode == "Append"
                            else normalized_upload_df
                        )
                        is_valid, duplicate_rows = validate_unique_keys(dataset_name, combined_df)
                        validation_errors = validate_dataset_rules(dataset_name, combined_df)
                        if not is_valid:
                            unique_keys = DATASETS[dataset_name].get("unique_keys", [])
                            st.error(
                                f"Duplicate key detected while importing into {dataset_name}. "
                                f"The columns {', '.join(unique_keys)} must be unique."
                            )
                            st.dataframe(duplicate_rows, use_container_width=True, height=220)
                        elif validation_errors:
                            for error in validation_errors:
                                st.error(error)
                        else:
                            save_dataset(dataset_name, combined_df)
                            log_audit_action(
                                "admin_import",
                                dataset_name,
                                {
                                    "mode": upload_mode.lower(),
                                    "imported_rows": len(normalized_upload_df),
                                    "final_row_count": len(combined_df),
                                },
                            )
                            st.success(
                                f"Imported {len(normalized_upload_df)} row(s) into {dataset_name} using {upload_mode.lower()} mode."
                            )
                    except Exception as exc:
                        st.error(f"Could not import into {dataset_name}: {exc}")

        st.markdown("**Recent Admin Activity**")
        audit_log_df = fetch_audit_log(limit=20)
        st.dataframe(audit_log_df, use_container_width=True, height=220)
