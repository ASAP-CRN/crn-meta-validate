"""
Streamlit rendering layer for the ASAP CRN metadata QC app.

Wraps the pure-Python validation logic in `utils.validate_core` with
Streamlit widgets, session-state management, and dataframe previews.
Import this module only from Streamlit app code; external tooling should
import from `utils.validate_core` directly.
"""

import logging

import pandas as pd
import streamlit as st

from utils.validate_core import (
    NULL,
    ReportCollector,
    compose_validation_report,
    emoji_success,
    emoji_warning,
    normalize_null_like_dataframe,
    parse_literal_list,
    validate_table_eval,
)
from utils.delimiter_handler import format_dataframe_for_preview, build_styled_preview_with_differences
from utils.help_menus import build_hover_text_from_description, build_free_text_header_markdown


def _render_entries_to_streamlit(entries: list[tuple]) -> None:
    """Replay a list of ReportCollector entries to the active Streamlit context."""
    for msg_type, msg in entries:
        if msg_type == "markdown":
            st.markdown(msg)
        elif msg_type == "success":
            st.success(msg)
        elif msg_type == "error":
            st.error(msg)
        elif msg_type == "warning":
            st.warning(msg)
        elif msg_type == "header":
            st.header(msg)
        elif msg_type == "subheader":
            st.subheader(msg)
        elif msg_type == "divider":
            st.divider()


def build_bullet_invalid_details_markdown(
        column_name: str,
        hover_text: str,
        column_type: str,
        n_invalid_vals: int,
        invalid_descr: str,
        valid_descr: str,
        table_name: str,
        ) -> None:

    # HTML bullet with hover tooltip around column_name
    bullet_text = f"""
    <ul style="margin:0; padding-left:20px;">
    <li>
        <b>{column_type}</b> column
        <span class="tooltip-wrapper">
            <span class="missing-hover">{column_name}</span>
            <span class="tooltip-text">{hover_text}</span>
        </span>
        has {n_invalid_vals} invalid values:
        <ul style="margin-top:4px;">
            <li><b>Invalid values:</b> {invalid_descr}</li>
            <li><b>Expected:</b> {valid_descr}</li>
        </ul>
    </li>
    </ul>
    """
    return bullet_text


def build_bullet_missing_details_markdown(
        column_name: str,
        hover_text: str,
        column_type: str,
        table_name: str,
        ) -> str:
    """Return an HTML bullet describing a missing column, with hover text on the column name."""
    bullet_text = f"""
    <ul style="margin:0; padding-left:20px;">
    <li>
        <b>{column_type}</b> column
        <span class="tooltip-wrapper">
            <span class="missing-hover">{column_name}</span>
            <span class="tooltip-text">{hover_text}</span>
        </span>
        is missing in <b><i>{table_name}</i></b>
    </li>
    </ul>
    """
    return bullet_text


def get_hover_text_for_column(
    cde_rules: "pd.DataFrame",
    column_name: str,
) -> str:
    """Return hover text for a column using the CDE Description when available."""
    description_text = ""
    if (
        cde_rules is not None
        and hasattr(cde_rules, "columns")
        and "Description" in cde_rules.columns
        and "Field" in cde_rules.columns
    ):
        entry_mask = cde_rules["Field"] == column_name
        try:
            description_value = cde_rules.loc[entry_mask, "Description"].iloc[0]
        except (KeyError, IndexError):
            description_value = ""
        if pd.notna(description_value):
            description_text = str(description_value)

    return build_hover_text_from_description(description_text)


def render_missing_columns(
    *,
    validation_report: "ReportCollector",
    table_name: str,
    cde_rules: "pd.DataFrame",
    table_comments: dict[str, str],
    missing_columns: list[str],
    total_columns: int,
    column_type_label: str,
    widget_key_prefix: str,
) -> None:
    """Render missing-column bullets + per-column comment boxes, and log to validation_report."""
    if not missing_columns:
        return

    summary_text = (
        f"**Missing {column_type_label.lower()} columns ({len(missing_columns)}/{total_columns}):**"
    )
    validation_report.entries.append(("markdown", summary_text))
    st.markdown(summary_text)

    for entry_index, column_name in enumerate(missing_columns):
        hover_text = get_hover_text_for_column(cde_rules, column_name)
        free_text_markdown = build_free_text_header_markdown(column_name, hover_text)
        bullet_text = build_bullet_missing_details_markdown(
            column_name,
            hover_text,
            column_type_label,
            table_name,
        )

        validation_report.entries.append(("markdown", bullet_text))

        values_column, comments_column = st.columns(2)

        with values_column:
            st.markdown(bullet_text, unsafe_allow_html=True)

        with comments_column:
            existing_comment_text = table_comments.get(column_name, "")
            comment_widget_key = (
                f"{widget_key_prefix}_{table_name}_{column_name}_{entry_index}"
            )

            if comment_widget_key not in st.session_state:
                st.session_state[comment_widget_key] = existing_comment_text

            st.markdown(free_text_markdown, unsafe_allow_html=True)
            comment_value = st.text_area(
                "Free text comment box",
                key=comment_widget_key,
                height=15,
                label_visibility="collapsed",
            )
            table_comments[column_name] = comment_value


def render_invalid_values(
    *,
    validation_report: "ReportCollector",
    table_name: str,
    cde_rules: "pd.DataFrame",
    table_comments: dict[str, str],
    invalid_entries: list[tuple[str, str, int, str, str]],
    widget_key_prefix: str,
) -> None:
    """Render invalid-value bullets + per-column comment boxes, and log to validation_report."""
    if not invalid_entries:
        return

    header_text = (
    f"<b>Columns not matching CDE controlled vocabularies in "
    f"<i>{table_name}</i>:</b>"
    )
    validation_report.entries.append(("markdown", header_text))
    st.markdown(header_text, unsafe_allow_html=True)

    for entry_index, (opt_req_flag, column_name, n_invalid_vals, valid_descr, invalid_descr) in enumerate(
        invalid_entries,
    ):
        column_type = opt_req_flag[0] + opt_req_flag[1:].lower()

        hover_text = get_hover_text_for_column(cde_rules, column_name)
        free_text_markdown = build_free_text_header_markdown(column_name, hover_text)
        bullet_text = build_bullet_invalid_details_markdown(
            column_name,
            hover_text,
            column_type,
            n_invalid_vals,
            invalid_descr,
            valid_descr,
            table_name,
        )

        validation_report.entries.append(("markdown", bullet_text))

        values_column, comments_column = st.columns(2)

        with values_column:
            st.markdown(bullet_text, unsafe_allow_html=True)

        with comments_column:
            existing_comment_text = table_comments.get(column_name, "")
            comment_widget_key = (
                f"{widget_key_prefix}_{table_name}_{column_name}_{entry_index}"
            )

            if comment_widget_key not in st.session_state:
                st.session_state[comment_widget_key] = existing_comment_text

            st.markdown(free_text_markdown, unsafe_allow_html=True)
            comment_value = st.text_area(
                "Free text comment box",
                key=comment_widget_key,
                height=15,
                label_visibility="collapsed",
            )

            table_comments[column_name] = comment_value


def validate_cde_vs_schema(cde_dataframe: pd.DataFrame, app_schema: dict, keys_cde, keys_json) -> bool:
    """
    Compare CDE Validation values vs JSON values/keys for a given pair definition.

    Parameters
    ----------
    cde_dataframe : pd.DataFrame
        CDE dataframe (as returned by utils.cde.read_CDE).
    app_schema : dict
        Parsed app schema JSON dict.
    keys_cde : tuple[str, str]
        ("TABLE", "field")
    keys_json : tuple[str, str]
        ("parent", "child") - child can be either list or dict (keys)
    """
    logger = logging.getLogger(__name__)

    # Get CDE values
    cde_table, cde_field = keys_cde
    cde_values = cde_dataframe[(cde_dataframe["Table"] == cde_table) & (cde_dataframe["Field"] == cde_field)]
    if cde_values.empty:
        raise ValueError(f"No CDE row found for Table={cde_table!r}, Field={cde_field!r}")
    cde_validation_raw = cde_values.iloc[0].get("Validation")
    cde_list = parse_literal_list(cde_validation_raw)

    # Get JSON values
    json_parent, json_child = keys_json
    if isinstance(app_schema[json_parent][json_child], list):
        json_list = app_schema[json_parent][json_child]
    elif isinstance(app_schema[json_parent][json_child], dict):
        json_list = list(app_schema[json_parent][json_child].keys())
    else:
        raise ValueError(f"Unexpected type for app_schema[{json_parent}][{json_child}]: {type(app_schema[json_parent][json_child])}")

    # Compare CDE vs Schema (JSON)
    cde_set = set(map(str, cde_list))
    json_set = set(map(str, json_list))
    only_in_cde = sorted(cde_set - json_set)
    only_in_json = sorted(json_set - cde_set)
    label_left = f"CDE:{cde_table}:{cde_field}:Validation"
    label_right = f"schema:{json_parent}:{json_child}:keys"
    if only_in_cde or only_in_json:
        if only_in_cde:
            logger.warning("%s has values not in %s: %s", label_left, label_right, only_in_cde)
            st.warning(f"{emoji_warning} Warning!!! {label_left} has values not in {label_right}: {only_in_cde}")
        if only_in_json:
            logger.warning("%s has values not in %s: %s", label_right, label_left, only_in_json)
            st.warning(f"{emoji_warning} Warning!!! {label_right} has values not in {label_left}: {only_in_json}")
        return False

    logger.info("OK: %s matches %s", label_left, label_right)
    return True


def decide_cde_vs_schema_validation(
        app_schema_version: str,
        cde_dataframe: pd.DataFrame,
        app_schema: dict,
        ):
    """
    Decide whether to validate app_schema categories against CDE Validation lists or not

    Parameters
    ----------
    app_schema_version : str
        App schema version string, e.g. "v0.4", "v0.5", etc.
    """
    ### validate_cde_vs_schema function was defined for app_schema v0.8 but deprecated in v0.9 because we are reading directly from the CDE
    ### Keeping this function for backward compatibility with v0.8 apps and CDE vs. JSON debugging purposes.
    schemas_that_need_validation_vs_cde = ["v0.8"]

    if app_schema_version in schemas_that_need_validation_vs_cde:

        ## Input as: validate_cde_vs_schema(cde_dataframe, app_schema, CDE:(table, field), schema:(schema_section, schema_field))
        species_match = validate_cde_vs_schema(
            cde_dataframe,
            app_schema,
            ("SAMPLE", "organism"),
            ("table_categories", "species")
        )
        sample_source_match = validate_cde_vs_schema(
            cde_dataframe,
            app_schema,
            ("ASSAY", "sample_source"),
            ("table_categories", "sample_source")
        )
        assays_match = validate_cde_vs_schema(
            cde_dataframe,
            app_schema,
            ("ASSAY", "assay"),
            ("table_categories", "assays")
        )
        if not species_match or not sample_source_match or not assays_match:
            st.warning(
                f"{emoji_warning} Warning!!! App configuration: app_schema table categories do not match the CDE Validation lists: "
                f"Species:{emoji_success if species_match else emoji_warning}, Sample Source:{emoji_success if sample_source_match else emoji_warning}, Assay:{emoji_success if assays_match else emoji_warning}."
            )


def validate_table_ui(df_after_fill: pd.DataFrame, table_name: str,
                   cde_rules: pd.DataFrame, validation_report: ReportCollector, df_raw_before_fill=None,
                   preview_max_rows=None, app_schema=None):
    """
    Validate the table against the specific table entries from the CDE.

    Parameters
    ----------
    df_after_fill : pd.DataFrame
        Table with CDE-required columns already filled in.
    table_name : str
        Name of the metadata table (e.g. ``"SUBJECT"``).
    cde_rules : pd.DataFrame
        CDE rules filtered to this table and OSA selection.
    validation_report : ReportCollector
        Collector to append messages to.
    df_raw_before_fill : pd.DataFrame or None
        Pre-fill snapshot used for the diff preview; defaults to `df_after_fill`.
    preview_max_rows : int or None
        Maximum rows shown in the Streamlit preview.
    app_schema : dict or None
        App schema dict providing preview colour codes.

    Returns
    -------
    tuple
        df_after_fill : pd.DataFrame
            Table after filling out missing columns with `NULL`.
        validation_report : ReportCollector
            Collector with all messages appended.
        errors_counter : int
            Count of blocking errors.
        warnings_counter : int
            Count of non-blocking warnings.
    """
    if df_raw_before_fill is not None:
        df_preview_before_fill = df_raw_before_fill.copy()
    else:
        df_preview_before_fill = df_after_fill.copy()

    df_after_fill = normalize_null_like_dataframe(df_after_fill, sentinel=NULL)

    result = validate_table_eval(df_after_fill, cde_rules)

    # Compose summary report; per-column details rendered below as Streamlit widgets.
    # Snapshot entries length first so we replay only the new entries to Streamlit.
    entries_before = len(validation_report.entries)
    errors_counter, warnings_counter = compose_validation_report(
        result, table_name, validation_report, include_details=False
    )
    _render_entries_to_streamlit(validation_report.entries[entries_before:])

    # Fill missing columns with NULL so the df is complete for downstream steps
    for column in result["missing_required"] + result["missing_optional"]:
        df_after_fill[column] = NULL

    invalid_cell_mask = result["invalid_cell_mask"]

    ############
    ### Preview of validated table
    st.markdown("---")
    st.markdown(
        f"""
        <div style="font-size:16px; font-weight:600;">
            Preview <i>{table_name}</i> <u>after</u> CDE comparison.
        </div>
        <div style="font-size:14px; margin-top:2px;">
            Color code: <span style="color:{app_schema['preview_fillout_color']}; font-weight:400;">filled out</span>,
            <span style="color:{app_schema['preview_invalid_cde_color']}; font-weight:400;">invalid vs. CDE</span>.
        </div>
        """,
        unsafe_allow_html=True,
    )

    rows_to_show = st.session_state.get("preview_max_rows", preview_max_rows)
    show_all_validated_key = f"show_all_rows_validated_{table_name}"
    show_all_validated = st.session_state.get(show_all_validated_key, False)
    if show_all_validated:
        preview_df_preview_before_fill = df_preview_before_fill
        preview_validated_df = df_after_fill
    else:
        preview_df_preview_before_fill = df_preview_before_fill.head(rows_to_show)
        preview_validated_df = df_after_fill.head(rows_to_show)

    # Align invalid-cell mask to the preview dataframe
    preview_invalid_mask = invalid_cell_mask.reindex_like(preview_validated_df)

    styled_preview = build_styled_preview_with_differences(
        preview_df_preview_before_fill,
        preview_validated_df,
        invalid_mask=preview_invalid_mask,
        app_schema=app_schema,
    )
    if styled_preview is not None:
        st.dataframe(styled_preview)
    else:
        st.dataframe(format_dataframe_for_preview(preview_validated_df))
    st.checkbox("Show all rows", key=show_all_validated_key, value=show_all_validated)
    st.markdown("---")

    missing_required = result["missing_required"]
    missing_optional = result["missing_optional"]
    invalid_entries  = result["invalid_entries"]
    total_required   = result["total_required"]
    total_optional   = result["total_optional"]

    ############
    #### Provide details of missing columns and invalid values per column

    #### Details of missing columns
    if missing_required or missing_optional:
        st.markdown("#### **Details of missing columns:**")

        # Track per-column comments (shared with invalid-value comments).
        column_comments = st.session_state.get("column_comments", {})
        if table_name not in column_comments:
            column_comments[table_name] = {}
        table_comments = column_comments[table_name]

        render_missing_columns(
            validation_report=validation_report,
            table_name=table_name,
            cde_rules=cde_rules,
            table_comments=table_comments,
            missing_columns=missing_required,
            total_columns=total_required,
            column_type_label="Required",
            widget_key_prefix="missing_comment",
        )
        render_missing_columns(
            validation_report=validation_report,
            table_name=table_name,
            cde_rules=cde_rules,
            table_comments=table_comments,
            missing_columns=missing_optional,
            total_columns=total_optional,
            column_type_label="Optional",
            widget_key_prefix="missing_comment",
        )

        column_comments[table_name] = table_comments
        st.session_state["column_comments"] = column_comments

    #### Details of invalid values per column
    if invalid_entries:
        st.markdown("#### **Details of invalid values per column:**")

        column_comments = st.session_state.get("column_comments", {})
        if table_name not in column_comments:
            column_comments[table_name] = {}
        table_comments = column_comments[table_name]

        render_invalid_values(
            validation_report=validation_report,
            table_name=table_name,
            cde_rules=cde_rules,
            table_comments=table_comments,
            invalid_entries=invalid_entries,
            widget_key_prefix="invalid_comment",
        )

        column_comments[table_name] = table_comments
        st.session_state["column_comments"] = column_comments

    return df_after_fill, validation_report, errors_counter, warnings_counter
