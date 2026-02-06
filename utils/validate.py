"""
Validate tables utilities for ASAP CRN metadata QC app

This module checks for handles loading and processing of CDE definitions from either
Google Sheets or local CSV files.

"""

from dataclasses import field
from utils.find_missing_values import NULL_SENTINEL, normalize_null_like_dataframe, compute_missing_mask
from utils.help_menus import build_hover_text_from_description, build_free_text_header_markdown
from utils.delimiter_handler import format_dataframe_for_preview, build_styled_preview_with_differences

NULL = NULL_SENTINEL  ## Canonical token used for null-like values in *_sanitized.csv files

import pandas as pd
import re
import streamlit as st
import logging
from ast import literal_eval
import time

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

def get_extra_columns_not_in_cde(
    table_name: str,
    table_df: "pd.DataFrame",
    table_cde_rules: "pd.DataFrame",
) -> list[str]:
    """
    Return a sorted list of columns that are present in the input table_df
    but not defined in the CDE for this table (table_cde_rules["Field"]).
    """
    extra_fields: list[str] = []
    try:
        cde_fields = set(table_cde_rules["Field"].astype(str))
        input_fields = set(table_df.columns.astype(str))
        extra_fields = sorted(input_fields - cde_fields)
    except Exception:
        extra_fields = []
    return extra_fields

def get_log(log_file):
    """ grab logged information from the log file."""
    with open(log_file, 'r') as f:
        report_content = f.read()
    return report_content

def columnize( itemlist ):
    NEWLINE_DASH = ' \n- '
    if len(itemlist) > 1:
        return f"- {itemlist[0]}{NEWLINE_DASH.join(itemlist[1:])}"
    else:
        return f"- {itemlist[0]}"
    
def read_meta_table(table_path):
    # read the whole table
    try:
        table_df = pd.read_csv(table_path,dtype=str)
    except UnicodeDecodeError:
        table_df = pd.read_csv(table_path, encoding='latin1',dtype=str)

    # drop the first column if it is just the index
    if table_df.columns[0] == "Unnamed: 0":
        table_df = table_df.drop(columns=["Unnamed: 0"])
        
    return table_df

def parse_literal_list(raw):
    if raw is None:
        return []
    raw = str(raw).strip()
    if not raw:
        return []

    val = literal_eval(raw)
    if isinstance(val, list):
        return val
    else:
        return [val] # force to list


def get_hover_text_for_column(
    specific_cde_df: "pd.DataFrame",
    column_name: str,
) -> str:
    """Return hover text for a column using the CDE Description when available."""
    description_text = ""
    if (
        specific_cde_df is not None
        and hasattr(specific_cde_df, "columns")
        and "Description" in specific_cde_df.columns
        and "Field" in specific_cde_df.columns
    ):
        entry_mask = specific_cde_df["Field"] == column_name
        try:
            description_value = specific_cde_df.loc[entry_mask, "Description"].iloc[0]
        except (KeyError, IndexError):
            description_value = ""
        if pd.notna(description_value):
            description_text = str(description_value)

    return build_hover_text_from_description(description_text)


def render_missing_columns(
    *,
    validation_report: "ReportCollector",
    table_name: str,
    specific_cde_df: "pd.DataFrame",
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
        hover_text = get_hover_text_for_column(specific_cde_df, column_name)
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
    specific_cde_df: "pd.DataFrame",
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

        hover_text = get_hover_text_for_column(specific_cde_df, column_name)
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

class ReportCollector:
    """
    Class to collect and log messages, errors, and markdown to a log file and/or streamlit
    """

    def __init__(self, destination="both"):
        self.entries = []
        self.filename = None

        if destination in ["both", "streamlit"]:
            self.publish_to_streamlit = True
        else:
            self.publish_to_streamlit = False

    def add_markdown(self, msg):
        self.entries.append(("markdown", msg))
        if self.publish_to_streamlit:
            st.markdown(msg)

    def add_success(self, msg):
        self.entries.append(("success", msg))
        if self.publish_to_streamlit:
            st.success(msg)

    def add_error(self, msg):
        self.entries.append(("error", msg))
        if self.publish_to_streamlit:
            st.error(msg)

    def add_warning(self, msg):
        self.entries.append(("warning", msg))
        if self.publish_to_streamlit:
            st.warning(msg)

    def add_header(self, msg):
        self.entries.append(("header", msg))
        if self.publish_to_streamlit:    
            st.header(msg)

    def add_subheader(self, msg):
        self.entries.append(("subheader", msg))
        if self.publish_to_streamlit:    
            st.subheader(msg)

    def add_divider(self):
        self.entries.append(("divider", None))
        if self.publish_to_streamlit:    
            st.divider()

    
    def write_to_file(self, filename):
        self.filename = filename
        with open(filename, 'w') as f:
            report_content = self.get_log()
            f.write(report_content)
    

    def get_log(self):
        """ grab logged information from the log file."""
        report_content = []
        for msg_type, msg in self.entries:
            if msg_type == "markdown":
                report_content += f"{msg}\n"
            elif msg_type == "error":
                report_content += f"{msg}\n"
            elif msg_type == "header":
                report_content += f"# {msg}\n"
            elif msg_type == "subheader":
                report_content += f"## {msg}\n"
            elif msg_type == "divider":
                report_content += 60*'-' + '\n'
        
        return "".join(report_content)

    def reset(self):
        self.entries = []
        self.filename = None

    def print_log(self):
        print(self.get_log())

def decide_cde_vs_schema_validation(
        app_schema_version: str,
        cde_dataframe: pd.DataFrame,
        app_schema: dict,
        ): 
    """
    Decide whether to validate app_schema categories against CDE Validation lists or not
    
    Parameters
    ----------
    app_schema_version: str
        App schema version string, e.g. "v0.4", "v0.5", etc.
    """
    logger = logging.getLogger(__name__)

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
                f"⚠️ Warning!!! App configuration: app_schema table categories do not match the CDE Validation lists: "
                f"Species:{'✅' if species_match else '⚠️'}, Sample Source:{'✅' if sample_source_match else '⚠️'}, Assay:{'✅' if assays_match else '⚠️'}."
            )

def validate_cde_vs_schema(cde_dataframe: pd.DataFrame, app_schema: dict, keys_cde, keys_json) -> bool:
    """
    Compare CDE Validation values vs JSON values/keys for a given pair definition.

    Parameters
    ----------
    cde_dataframe: pd.DataFrame
        CDE dataframe (as returned by utils.cde.read_CDE).
    app_schema: dict
        Parsed app schema JSON dict.
    keys_cde: touple[str, str]
        ("TABLE", "field")
    keys_json: touple[str, str]
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
            st.warning(f"⚠️ Warning!!! {label_left} has values not in {label_right}: {only_in_cde}")
        if only_in_json:
            logger.warning("%s has values not in %s: %s", label_right, label_left, only_in_json)
            st.warning(f"⚠️ Warning!!! {label_right} has values not in {label_left}: {only_in_json}")
        return False

    logger.info("OK: %s matches %s", label_left, label_right)
    return True

def validate_table(df_after_fill: pd.DataFrame, table_name: str, 
                   specific_cde_df: pd.DataFrame, validation_report: ReportCollector, df_raw_before_fill=None, 
                   preview_max_rows=None, app_schema=None):
    """
    Validate the table against the specific table entries from the CDE

    Returns:
    table_df: pd.DataFrame after filling out empty cells
    validation_report: ReportCollector with validation messages
    errors_counter: int counting the number of errors found
    warnings_counter: int counting the number of warnings found
    """
    errors_counter = 0
    warnings_counter = 0

    ############
    if df_raw_before_fill is not None:
        df_preview_before_fill = df_raw_before_fill.copy()
    else:
        df_preview_before_fill = df_after_fill.copy()

    # Snapshot of the table *after* user fill-out but *before* null-like normalization.
    # This is used to count truly missing cells (empty / NA) for the Step 5 summary,
    # so that filling values in Step 4 actually clears "empty values" errors.
    df_for_missing_check = df_after_fill.copy()

    ############
    #### Replace empty strings and various null representations with NULL_SENTINEL
    df_after_fill = normalize_null_like_dataframe(df_after_fill, sentinel=NULL)

    # Track per-cell invalid values (those not matching Validation or FillNull)
    invalid_cell_mask = pd.DataFrame(False, index=df_after_fill.index, columns=df_after_fill.columns)

    def my_str(x):
        return f"'{str(x)}'"

    ############
    #### Record:
    #### a) missing required and optional columns
    #### b) columns present but full of empty string
    #### c) invalid entries in columns (not matching expected values according to CDE)
    missing_required = []
    missing_optional = []
    invalid_required = []
    invalid_optional = []
    null_columns = []
    invalid_entries = []
    total_required = 0
    total_optional = 0
    for column in specific_cde_df["Field"]:
        entry_idx = specific_cde_df["Field"]==column

        opt_req = "REQUIRED" if specific_cde_df.loc[entry_idx, "Required"].item()=="Required" else "OPTIONAL"
        if opt_req == "REQUIRED":
            total_required += 1
        else:
            total_optional += 1

        if column not in df_after_fill.columns:
            if opt_req == "REQUIRED":
                missing_required.append(column)
            else:
                missing_optional.append(column)
        else:
            datatype = specific_cde_df.loc[entry_idx,"DataType"]

            # Test that Integer columns are all int or NULL or allowed FillNull strings
            if datatype.item() == "Integer":
                # Allowed special non-numeric tokens for this column (e.g. "Not Reported", "Unknown", "NA")
                fillnull_values_raw = specific_cde_df.loc[entry_idx, "FillNull"].item()
                fillnull_values = parse_literal_list(fillnull_values_raw)
                allowed_specials = set(fillnull_values)
                allowed_specials.add(NULL_SENTINEL)

                entries = df_after_fill[column]

                # Values that match allowed FillNull tokens (including canonical NULL) are always valid
                is_special = entries.isin(allowed_specials)

                # For the remaining values, require that they are integer-like numbers
                numeric = pd.to_numeric(entries, errors="coerce")
                is_integer_numeric = numeric.notna() & ((numeric % 1) == 0)

                valid_mask = is_special | is_integer_numeric
                invalid_mask = ~valid_mask
                invalid_cell_mask.loc[invalid_mask, column] = True

                invalid_values = entries[invalid_mask].unique()
                n_invalid = invalid_values.shape[0]
                if n_invalid > 0:
                    valstr = f"int or NULL ('{NULL_SENTINEL}') or FillNull values ({', '.join(map(my_str, fillnull_values))})"
                    invalstr = ', '.join(map(my_str, invalid_values))
                    invalid_entries.append((opt_req, column, n_invalid, valstr, invalstr))
                    invalid_required.append(column) if opt_req == "REQUIRED" else invalid_optional.append(column)

            # Test that Float columns are all float or NULL or allowed FillNull strings
            elif datatype.item() == "Float":
                # Allowed special non-numeric tokens for this column (e.g. "Not Reported", "Unknown", "NA")
                fillnull_values_raw = specific_cde_df.loc[entry_idx, "FillNull"].item()
                fillnull_values = parse_literal_list(fillnull_values_raw)
                allowed_specials = set(fillnull_values)
                allowed_specials.add(NULL_SENTINEL)

                entries = df_after_fill[column]

                # Values that match allowed FillNull tokens (including canonical NULL) are always valid
                is_special = entries.isin(allowed_specials)

                # For the remaining values, require that they are float-like numbers
                numeric = pd.to_numeric(entries, errors="coerce")
                is_float_numeric = numeric.notna()

                valid_mask = is_special | is_float_numeric
                invalid_mask = ~valid_mask
                invalid_cell_mask.loc[invalid_mask, column] = True

                invalid_values = entries[invalid_mask].unique()
                n_invalid = invalid_values.shape[0]
                if n_invalid > 0:
                    valstr = f"float or NULL ('{NULL_SENTINEL}') or FillNull values ({', '.join(map(my_str, fillnull_values))})"
                    invalstr = ', '.join(map(my_str, invalid_values))
                    invalid_entries.append((opt_req, column, n_invalid, valstr, invalstr))
                    invalid_required.append(column) if opt_req == "REQUIRED" else invalid_optional.append(column)

            # Test that Enum types match CDE Validation (controlled vocabularies) or FillNull (allowed null representations)
            elif datatype.item() == "Enum":
                # Get list of allowed Valid values from CDE
                validation_raw = specific_cde_df.loc[entry_idx,"Validation"].item()
                valid_values = parse_literal_list(validation_raw)

                # Get list of allowed FillNull values from CDE
                fillnull_values_raw = specific_cde_df.loc[entry_idx,"FillNull"].item()
                fillnull_values = parse_literal_list(fillnull_values_raw)

                # Merge Valid + FillNull
                valid_and_fillnull_values = list(set(list(valid_values + fillnull_values)))

                entries = df_after_fill[column]
                valid_entries = entries.apply(lambda x: x in valid_and_fillnull_values)
                invalid_mask = ~valid_entries
                invalid_cell_mask.loc[invalid_mask, column] = True
                invalid_values = entries[~valid_entries].unique()
                n_invalid = invalid_values.shape[0]
                if n_invalid > 0:
                    valstr = ', '.join(map(my_str, valid_and_fillnull_values))
                    invalstr = ', '.join(map(my_str,invalid_values))
                    invalid_entries.append((opt_req, column, n_invalid, valstr, invalstr))
                    invalid_required.append(column) if opt_req=="REQUIRED" else invalid_optional.append(column)

            elif datatype.item() == "Regex":
                # Regex DataType: value must either match the pattern or be one of the FillNull tokens.
                validation_raw = specific_cde_df.loc[entry_idx, "Validation"].item()
                pattern = str(validation_raw).strip()
                fillnull_values_raw = specific_cde_df.loc[entry_idx, "FillNull"].item()
                fillnull_values = parse_literal_list(fillnull_values_raw)

                entries = df_after_fill[column]

                def is_valid_regex_entry(entry_value):
                    if entry_value in fillnull_values:
                        return True
                    if entry_value == NULL_SENTINEL:
                        # Treat true nulls as invalid for Regex fields unless explicitly allowed via FillNull.
                        return entry_value in fillnull_values
                    try:
                        return re.fullmatch(pattern, str(entry_value)) is not None
                    except re.error:
                        # If the pattern itself is invalid, treat all entries as invalid for this column.
                        return False

                valid_entries = entries.apply(is_valid_regex_entry)
                invalid_mask = ~valid_entries
                invalid_cell_mask.loc[invalid_mask, column] = True

                invalid_values = entries[invalid_mask].unique()
                n_invalid = invalid_values.shape[0]
                if n_invalid > 0:
                    valstr = f"Regex /{pattern}/ or FillNull values ({', '.join(map(my_str, fillnull_values))})"
                    invalstr = ", ".join(map(my_str, invalid_values))
                    invalid_entries.append((opt_req, column, n_invalid, valstr, invalstr))
                    if opt_req == "REQUIRED":
                        invalid_required.append(column)
                    else:
                        invalid_optional.append(column)

            # Freeform dtype == String
            else:
                pass
            
            if column in df_for_missing_check.columns:
                missing_mask_for_column = compute_missing_mask(df_for_missing_check[column])
                n_null = int(missing_mask_for_column.sum())
                if n_null > 0:
                    null_columns.append((opt_req, column, n_null))

    ############
    #### Compose summary report and log of errors and warnings

    #### Report summary of --missing-- columns
    if len(missing_required) > 0:
        validation_report.add_error(f"❌ -- See details below: {len(missing_required)} of {total_required} **required** columns are missing in {table_name}\n")
        for column in missing_required:
            df_after_fill[column] = NULL
            errors_counter += 1
    else:
        validation_report.add_success(f"✅ -- All {total_required} **required** columns are present in {table_name}\n")

    if len(missing_optional) > 0:
        validation_report.add_warning(f"⚠️ -- See details below: {len(missing_optional)} of {total_optional} **optional** columns are missing in {table_name}\n")
        for column in missing_optional:
            df_after_fill[column] = NULL
            warnings_counter += 1
    else:
        validation_report.add_success(f"✅ -- All {total_optional} **optional** columns are present in {table_name}\n")

    #### Report summary of --invalid-- entries (i.e. not matching CDE)
    if len(invalid_required) > 0:
        validation_report.add_error(f"❌ -- See details below: {len(invalid_required)} of {total_required} **required** columns have invalid values in {table_name}\n")
        errors_counter += len(invalid_required)
    else:
        validation_report.add_success(f"✅ -- No invalid values were found in required columns\n")

    if len(invalid_optional) > 0:
        validation_report.add_warning(f"⚠️ -- See details below: {len(invalid_optional)} of {total_optional} **optional** columns have invalid values in {table_name}\n")
        warnings_counter += len(invalid_optional)
    else:
        validation_report.add_success(f"✅ -- No invalid values were found in optional columns\n")

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

    ############
    #### Provide details of missing columns and invalid values per column

    #### Details of missing columns
    if len(missing_required) + len(missing_optional) > 0:
        header_text = "**Details of missing columns:**"

        # Log header for markdown QC report and show it once in the app.
        validation_report.entries.append(("markdown", header_text))
        st.markdown(f"#### {header_text}")

        # Track per-column comments (shared with invalid-value comments).
        column_comments = st.session_state.get("column_comments", {})
        if table_name not in column_comments:
            column_comments[table_name] = {}
        table_comments = column_comments[table_name]

        render_missing_columns(
            validation_report=validation_report,
            table_name=table_name,
            specific_cde_df=specific_cde_df,
            table_comments=table_comments,
            missing_columns=missing_required,
            total_columns=total_required,
            column_type_label="Required",
            widget_key_prefix="missing_comment",
        )
        render_missing_columns(
            validation_report=validation_report,
            table_name=table_name,
            specific_cde_df=specific_cde_df,
            table_comments=table_comments,
            missing_columns=missing_optional,
            total_columns=total_optional,
            column_type_label="Optional",
            widget_key_prefix="missing_comment",
        )

        column_comments[table_name] = table_comments
        st.session_state["column_comments"] = column_comments

    #### Details of invalid values per column
    if len(invalid_entries) > 0:
        header_text = "**Details of invalid values per column:**"

        # Log header for markdown QC report and show it once in the app.
        validation_report.entries.append(("markdown", header_text))
        st.markdown(f"#### {header_text}")

        column_comments = st.session_state.get("column_comments", {})
        if table_name not in column_comments:
            column_comments[table_name] = {}
        table_comments = column_comments[table_name]

        render_invalid_values(
            validation_report=validation_report,
            table_name=table_name,
            specific_cde_df=specific_cde_df,
            table_comments=table_comments,
            invalid_entries=invalid_entries,
            widget_key_prefix="invalid_comment",
        )

        column_comments[table_name] = table_comments
        st.session_state["column_comments"] = column_comments

    return df_after_fill, validation_report, errors_counter, warnings_counter

def get_invalid_status_rows(
        df_with_status: pd.DataFrame,
        expected_status: str,
        transient_statuses: list[str]):
    """
    Given a DataFrame with a "Status" column, return three DataFrames:
    1) Rows where Status is not equal to expected_status
    2) Rows where Status is in transient_statuses
    3) Rows where Status is neither expected_status nor in transient_statuses

    Parameters
    ----------
    df_with_status: pd.DataFrame
        DataFrame containing a "Status" column.
    expected_status: str
        The expected valid status value (e.g., "Ok: found in CDE_current").
    transient_statuses: list[str]
        List of transient status values (e.g., ["Loading...", ""]).
    
    Returns
    ------- 
    invalid_rows: pd.DataFrame
        Rows where Status is not equal to expected_status.
    transient_rows: pd.DataFrame
        Rows where Status is in transient_statuses.
    hard_invalid_rows: pd.DataFrame
        Rows where Status is neither expected_status nor in transient_statuses.
    """
    
    status_series = (
        df_with_status["Status"]
        .fillna("")
        .astype(str)
        .str.strip()
    )
    invalid_rows = df_with_status[status_series != expected_status]
    transient_rows = df_with_status[status_series.isin(transient_statuses)]
    hard_invalid_rows = df_with_status[
        (status_series != expected_status) & (~status_series.isin(transient_statuses))
    ]
    return invalid_rows, transient_rows, hard_invalid_rows

def read_valid_categories_with_status_retry(
        load_df_with_status_fn: callable,
        max_tries: int,
        sleep_seconds: int,
        expected_status: str,
        transient_statuses: list[str],
    ) -> pd.DataFrame:
    """
    Attempt to load the valid categories DataFrame multiple times, retrying if
    there are any transient invalid statuses.

    Parameters
    ----------
    load_df_with_status_fn: callable
        Function that returns the DataFrame with column 'Status' when called.
    max_tries: int
        Maximum number of attempts to load the DataFrame.
    sleep_seconds: int
        Number of seconds to wait between attempts.
    expected_status: str
        The expected valid status value.
    transient_statuses: list[str]
        List of transient status values.

    Returns
    -------
    pd.DataFrame
        The DataFrame with column 'Status' after retries.
    """

    for attempt_index in range(1, max_tries + 1):
        last_df = load_df_with_status_fn()
        invalid_rows, transient_rows, hard_invalid_rows = get_invalid_status_rows(last_df, expected_status, transient_statuses)

        # If everything is OK, proceed.
        if invalid_rows.empty:
            return last_df

        # If we have any hard invalid values, fail immediately (not a transient timing issue).
        if not hard_invalid_rows.empty:
            return last_df  # caller will handle as error

        # Only transient statuses remain -> retry after a short delay.
        if attempt_index < max_tries:
            time.sleep(sleep_seconds)

    return last_df
