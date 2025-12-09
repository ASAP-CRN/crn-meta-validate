"""
Validate tables utilities for ASAP CRN metadata QC app

This module checks for handles loading and processing of CDE definitions from either
Google Sheets or local CSV files.

"""

from utils.find_missing_values import NULL_SENTINEL, normalize_null_like_dataframe, compute_missing_mask
from utils.help_menus import build_hover_text_from_description, build_free_text_header_markdown
from utils.delimiter_handler import format_dataframe_for_preview, build_styled_preview_with_differences

NULL = NULL_SENTINEL  ## Canonical token used for null-like values in *_sanitized.csv files

import pandas as pd
import re
import html
import streamlit as st
from ast import literal_eval

def build_bullet_invalid_details_markdown(
        column_name: str, hover_text: str, 
        column_type: str, n_invalid_vals: int, 
        invalid_descr: str, valid_descr: str) -> None:
    
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

def validate_table(table_df: pd.DataFrame, table_name: str, specific_cde_df: pd.DataFrame, validation_report: ReportCollector, not_filled_table=None, preview_max_rows=None):
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
    if not_filled_table is not None:
        original_df = not_filled_table.copy()
    else:
        original_df = table_df.copy()

    ############
    #### Replace empty strings and various null representations with NULL_SENTINEL
    table_df = normalize_null_like_dataframe(table_df, sentinel=NULL)
    
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

        if column not in table_df.columns:
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

                entries = table_df[column]

                # Values that match allowed FillNull tokens (including canonical NULL) are always valid
                is_special = entries.isin(allowed_specials)

                # For the remaining values, require that they are integer-like numbers
                numeric = pd.to_numeric(entries, errors="coerce")
                is_integer_numeric = numeric.notna() & ((numeric % 1) == 0)

                valid_mask = is_special | is_integer_numeric
                invalid_mask = ~valid_mask

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

                entries = table_df[column]

                # Values that match allowed FillNull tokens (including canonical NULL) are always valid
                is_special = entries.isin(allowed_specials)

                # For the remaining values, require that they are float-like numbers
                numeric = pd.to_numeric(entries, errors="coerce")
                is_float_numeric = numeric.notna()

                valid_mask = is_special | is_float_numeric
                invalid_mask = ~valid_mask

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

                entries = table_df[column]
                valid_entries = entries.apply(lambda x: x in valid_and_fillnull_values)
                invalid_values = entries[~valid_entries].unique()
                n_invalid = invalid_values.shape[0]
                if n_invalid > 0:
                    valstr = ', '.join(map(my_str, valid_and_fillnull_values))
                    invalstr = ', '.join(map(my_str,invalid_values))
                    invalid_entries.append((opt_req, column, n_invalid, valstr, invalstr))
                    invalid_required.append(column) if opt_req=="REQUIRED" else invalid_optional.append(column)

            # Freeform dtype == String
            else:
                pass
            
            if column in original_df.columns:
                missing_mask_for_column = compute_missing_mask(original_df[column])
                n_null = int(missing_mask_for_column.sum())
                if n_null > 0:
                    null_columns.append((opt_req, column, n_null))


    ############
    #### Compose report, get error and warning counters to either provide the user with a download link for the sanitized file or not

    ## Report missing columns, either required (throw errors) or optional (throw warnings)
    if len(missing_required) > 0:
        validation_report.add_error(f"❌ -- Missing {len(missing_required)}/{total_required} **required** columns in *{table_name}*: {', '.join(missing_required)}")
        for column in missing_required:
            table_df[column] = NULL
            errors_counter += 1
    else:
        validation_report.add_success(f"✅ -- All {total_required} **required** columns are present in *{table_name}*")

    if len(missing_optional) > 0:
        validation_report.add_warning(f"⚠️ -- Missing {len(missing_optional)}/{total_optional} **optional** columns in *{table_name}*: {', '.join(missing_optional)}")
        for column in missing_optional:
            table_df[column] = NULL
            warnings_counter += 1
    else:
        validation_report.add_success(f"✅ -- All {total_optional} **optional** columns are present in *{table_name}*")

    ## Report columns with null/empty values, either required (throw errors) or optional (throw warnings)
    if len(null_columns) > 0:
        for opt_req, column, count in null_columns:
            if opt_req == "REQUIRED":
                validation_report.add_error(f"❌ -- **required** column _**{column}**_ has {count} empty values. Please fill them out with valid CDE values or 'Unknown' if that's the case, before uploading to Google buckets")
                errors_counter += 1
            else:
                validation_report.add_warning(f"⚠️ -- **optional** column _**{column}**_ has {count} empty values. You can opt to fill them out with valid CDE values or not before uploading to Google buckets")
                warnings_counter += 1
    else:
        validation_report.add_success(f"✅ -- No columns with empty values were found\n")

    ## Report summary of invalid entries (i.e. not matching CDE), either required (throw errors) or optional (throw warnings)
    if len(invalid_required) > 0:
        validation_report.add_error(f"❌ -- {len(invalid_required)} required columns with invalid values (details below): {', '.join(invalid_required)}")
        errors_counter += len(invalid_required)
    else:
        validation_report.add_success(f"✅ -- No invalid values were found in required columns\n")

    if len(invalid_optional) > 0:
        validation_report.add_warning(f"⚠️ -- {len(invalid_optional)} optional columns with invalid values: {', '.join(invalid_optional)}")
        warnings_counter += len(invalid_optional)
    else:
        validation_report.add_success(f"✅ -- No invalid values were found in optional columns\n")

    ############
    ### Preview of validated table
    st.markdown("---")
    st.markdown(
        f'###### Preview _{table_name}_ after CDE comparison',
        unsafe_allow_html=True
    )
    rows_to_show = st.session_state.get("preview_max_rows", preview_max_rows)
    show_all_validated_key = f"show_all_rows_validated_{table_name}"
    show_all_validated = st.session_state.get(show_all_validated_key, False)
    if show_all_validated:
        preview_original_df = original_df
        preview_validated_df = table_df
    else:
        preview_original_df = original_df.head(rows_to_show)
        preview_validated_df = table_df.head(rows_to_show)

    styled_preview = build_styled_preview_with_differences(
        preview_original_df,
        preview_validated_df,
    )
    if styled_preview is not None:
        st.dataframe(styled_preview)
    else:
        st.dataframe(format_dataframe_for_preview(preview_validated_df))
    st.checkbox("Show all rows", key=show_all_validated_key, value=show_all_validated)

    # Provide a detailed non-redundant list of invalid values per column
    if len(invalid_entries) > 0:
        header_text = (
            "**Details of invalid values by column (i.e. not matching CDE controlled vocabularies):**"
        )

        # Log header for markdown QC report and show it once in the app.
        validation_report.entries.append(("markdown", header_text))
        st.markdown(header_text)

        column_comments = st.session_state.get("column_comments", {})
        if table_name not in column_comments:
            column_comments[table_name] = {}
        table_comments = column_comments[table_name]

        for entry_index, (opt_req_flag, column_name, n_invalid_vals, valid_descr, invalid_descr) in enumerate(
            invalid_entries,
        ):
            column_type = opt_req_flag[0] + opt_req_flag[1:].lower()

            # Hover tooltip: use column Description from CDE when available
            description_text = ""
            if "Description" in specific_cde_df.columns:
                entry_idx = specific_cde_df["Field"] == column_name
                try:
                    description_value = specific_cde_df.loc[entry_idx, "Description"].iloc[0]
                except (KeyError, IndexError):
                    description_value = ""
                if pd.notna(description_value):
                    description_text = str(description_value)

            hover_text = build_hover_text_from_description(description_text)
            free_text_markdown = build_free_text_header_markdown(column_name, hover_text)
            bullet_text = build_bullet_invalid_details_markdown(
                column_name, hover_text,
                column_type, n_invalid_vals,
                invalid_descr, valid_descr
            )

            # Persist the detailed message for inclusion in the QC markdown log.
            validation_report.entries.append(("markdown", bullet_text))

            values_column, comments_column = st.columns(2)

            with values_column:
                st.markdown(bullet_text, unsafe_allow_html=True)
            with comments_column:
                existing_comment_text = table_comments.get(column_name, "")
                comment_widget_key = (
                    f"invalid_comment_{table_name}_{column_name}_{entry_index}"
                )

                if comment_widget_key not in st.session_state:
                    st.session_state[comment_widget_key] = existing_comment_text

                ### Free-text Add comment box
                st.markdown(free_text_markdown, unsafe_allow_html=True)
                comment_value = st.text_area(
                    "Free text comment box",
                    key=comment_widget_key,
                    height=15,
                    label_visibility="collapsed",
                )

                table_comments[column_name] = comment_value

        column_comments[table_name] = table_comments
        st.session_state["column_comments"] = column_comments
    return table_df, validation_report, errors_counter, warnings_counter

