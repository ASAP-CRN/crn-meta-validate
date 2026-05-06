"""
  Validation utilities for the ASAP CRN metadata QC app.
  Evaluates metadata TABLES vs CDE definitions.
  
  Two layers of API are provided:

  Streamlit-free (safe to import in any Python context):
    validate_table_core(df_normalised, cde_rules) -> dict
        Field-by-field CDE validation; returns raw result dict.
    compose_validation_report(result, table_name, report, include_details) -> (int, int)
        Translates a validate_table_core result into ReportCollector entries.
"""

import logging
import re
import time
from ast import literal_eval

import pandas as pd
import streamlit as st

from utils.find_missing_values import NULL_SENTINEL, normalize_null_like_dataframe
from utils.help_menus import build_hover_text_from_description, build_free_text_header_markdown
from utils.delimiter_handler import format_dataframe_for_preview, build_styled_preview_with_differences

NULL = NULL_SENTINEL  ## Canonical token used for null-like values in *_sanitized.csv files

emoji_success = "✅"
emoji_error   = "❌"
emoji_warning = "⚠️"

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
            st.warning(f"{emoji_warning} Warning!!! {label_left} has values not in {label_right}: {only_in_cde}")
        if only_in_json:
            logger.warning("%s has values not in %s: %s", label_right, label_left, only_in_json)
            st.warning(f"{emoji_warning} Warning!!! {label_right} has values not in {label_left}: {only_in_json}")
        return False

    logger.info("OK: %s matches %s", label_left, label_right)
    return True


def validate_table_core(
    df_normalised: pd.DataFrame,
    cde_rules: pd.DataFrame,
) -> dict:
    """
    Field-by-field validation of a normalised metadata table against CDE rules.

    Intentionally free of Streamlit imports so it can be used by other
    repositories that do not run inside a Streamlit context (e.g.
    asap-crn-cloud-dataset-metadata/utils/qc_metadata_utils.py).
    `validate_table` in this module wraps this function with Streamlit preview rendering.

    Parameters
    ----------
    df_normalised : pd.DataFrame
        Metadata table with null-like values already normalised to
        `NULL_SENTINEL` (call `normalize_null_like_dataframe` first).
    cde_rules : pd.DataFrame
        CDE rules filtered to the table being validated (one row per field).
        Must contain columns: `Field`, `Required`, `DataType`,
        `Validation`, `FillNull`, and optionally `AllowMultiEnum`.
        Rows with `Required == "Assigned"` are skipped.

    Returns
    -------
    dict
        missing_required : list[str]
            CDE Required fields absent from `df_normalised`.
        missing_optional : list[str]
            CDE Optional fields absent from `df_normalised`.
        invalid_required : list[str]
            Required fields containing at least one invalid value.
        invalid_optional : list[str]
            Optional fields containing at least one invalid value.
        all_null_required : list[str]
            Required fields where every row is `NULL_SENTINEL`.
        all_null_optional : list[str]
            Optional fields where every row is `NULL_SENTINEL`.
        null_columns : list[tuple[str, str, int]]
            `(opt_req, column, n_null)` for fields with some but not all
            null values.
        invalid_entries : list[tuple[str, str, int, str, str]]
            `(opt_req, column, n_invalid, expected_descr, found_descr)`
            for each field that fails validation.
        invalid_cell_mask : pd.DataFrame
            Boolean mask aligned to `df_normalised`; `True` where a cell
            is invalid.
        total_required : int
            Total number of Required (non-Assigned) CDE fields.
        total_optional : int
            Total number of Optional CDE fields.
    """
    _logger = logging.getLogger(__name__)

    missing_required: list[str] = []
    missing_optional: list[str] = []
    invalid_required: list[str] = []
    invalid_optional: list[str] = []
    all_null_required: list[str] = []
    all_null_optional: list[str] = []
    null_columns: list[tuple] = []
    invalid_entries: list[tuple] = []
    total_required = 0
    total_optional = 0
    invalid_cell_mask = pd.DataFrame(False, index=df_normalised.index, columns=df_normalised.columns)

    def _quote(x: object) -> str:
        return f"'{x}'"

    for _, row in cde_rules.iterrows():
        column = row["Field"]

        if row["Required"] == "Assigned":
            continue

        is_required = row["Required"] == "Required"
        opt_req = "REQUIRED" if is_required else "OPTIONAL"

        if is_required:
            total_required += 1
        else:
            total_optional += 1

        if column not in df_normalised.columns:
            (missing_required if is_required else missing_optional).append(column)
            continue

        col_values = df_normalised[column]
        datatype = row["DataType"]

        fillnull_values = parse_literal_list(row.get("FillNull", ""))
        allowed_specials = set(fillnull_values) | {NULL_SENTINEL}

        # All-null vs partial-null tracking
        n_null = int((col_values == NULL_SENTINEL).sum())
        if n_null == len(col_values) and len(col_values) > 0:
            (all_null_required if is_required else all_null_optional).append(column)
        elif n_null > 0:
            null_columns.append((opt_req, column, n_null))

        if datatype == "Integer":
            is_special = col_values.isin(allowed_specials)
            col_numeric = pd.to_numeric(col_values, errors="coerce")
            valid_mask = is_special | (col_numeric.notna() & ((col_numeric % 1) == 0))
            invalid_mask = ~valid_mask
            invalid_cell_mask.loc[invalid_mask, column] = True
            failing_values = col_values[invalid_mask].unique()
            if len(failing_values):
                expected_descr = (
                    f"int or NULL ('{NULL_SENTINEL}') or FillNull values "
                    f"({', '.join(map(_quote, fillnull_values))})"
                )
                invalid_entries.append((opt_req, column, len(failing_values),
                                        expected_descr, ', '.join(map(_quote, failing_values))))
                (invalid_required if is_required else invalid_optional).append(column)

        elif datatype == "Float":
            is_special = col_values.isin(allowed_specials)
            col_numeric = pd.to_numeric(col_values, errors="coerce")
            valid_mask = is_special | col_numeric.notna()
            invalid_mask = ~valid_mask
            invalid_cell_mask.loc[invalid_mask, column] = True
            failing_values = col_values[invalid_mask].unique()
            if len(failing_values):
                expected_descr = (
                    f"float or NULL ('{NULL_SENTINEL}') or FillNull values "
                    f"({', '.join(map(_quote, fillnull_values))})"
                )
                invalid_entries.append((opt_req, column, len(failing_values),
                                        expected_descr, ', '.join(map(_quote, failing_values))))
                (invalid_required if is_required else invalid_optional).append(column)

        elif datatype == "Enum":
            valid_values = parse_literal_list(row.get("Validation", ""))
            valid_and_fillnull = list(set(valid_values + fillnull_values))
            valid_values_set = set(valid_values)
            fillnull_values_set = set(fillnull_values)

            # AllowMultiEnum — Excel stores 1 as np.float64(1.0); str(1.0) == "1.0", not "1".
            if "AllowMultiEnum" not in cde_rules.columns:
                _logger.warning(
                    "AllowMultiEnum column missing from CDE dataframe. "
                    "Falling back to single-value Enum validation for all Enum fields."
                )
                allow_multi = False
            else:
                allow_multi_str = str(row["AllowMultiEnum"]).strip().lower() if row["AllowMultiEnum"] is not None else ""
                allow_multi = allow_multi_str in ("true", "1", "1.0", "yes")

            if allow_multi:
                def _is_valid_multi(cell_value,
                                    _fv=fillnull_values_set,
                                    _vv=valid_values_set):
                    if cell_value in _fv or cell_value == NULL_SENTINEL:
                        return True
                    tokens = [t.strip() for t in str(cell_value).split(";") if t.strip()]
                    return bool(tokens) and all(t in _vv for t in tokens)

                valid_entries = col_values.apply(_is_valid_multi)
            else:
                valid_entries = col_values.isin(set(valid_and_fillnull))

            invalid_mask = ~valid_entries
            invalid_cell_mask.loc[invalid_mask, column] = True
            failing_values = col_values[invalid_mask].unique()
            if len(failing_values):
                if allow_multi:
                    expected_descr = (
                        f"one or more values from the Validation list separated by ';' "
                        f"(e.g. 'val1;val2'), or a single FillNull value "
                        f"({', '.join(map(_quote, fillnull_values))}). "
                        f"Valid tokens: {', '.join(map(_quote, sorted(valid_values_set)))}"
                    )
                else:
                    expected_descr = ', '.join(map(_quote, valid_and_fillnull))
                invalid_entries.append((opt_req, column, len(failing_values),
                                        expected_descr, ', '.join(map(_quote, failing_values))))
                (invalid_required if is_required else invalid_optional).append(column)

        elif datatype == "Regex":
            pattern = str(row.get("Validation", "")).strip()

            def _is_valid_regex(val, _p=pattern, _sp=allowed_specials):
                if val in _sp:
                    return True
                try:
                    return re.fullmatch(_p, str(val)) is not None
                except re.error:
                    return False

            valid_entries = col_values.apply(_is_valid_regex)
            invalid_mask = ~valid_entries
            invalid_cell_mask.loc[invalid_mask, column] = True
            failing_values = col_values[invalid_mask].unique()
            if len(failing_values):
                expected_descr = (
                    f"Regex /{pattern}/ or FillNull values "
                    f"({', '.join(map(_quote, fillnull_values))})"
                )
                invalid_entries.append((opt_req, column, len(failing_values),
                                        expected_descr, ', '.join(map(_quote, failing_values))))
                (invalid_required if is_required else invalid_optional).append(column)

        # String: no restrictions

    return {
        "missing_required":  missing_required,
        "missing_optional":  missing_optional,
        "invalid_required":  invalid_required,
        "invalid_optional":  invalid_optional,
        "all_null_required": all_null_required,
        "all_null_optional": all_null_optional,
        "null_columns":      null_columns,
        "invalid_entries":   invalid_entries,
        "invalid_cell_mask": invalid_cell_mask,
        "total_required":    total_required,
        "total_optional":    total_optional,
    }


def compose_validation_report(
    result: dict,
    table_name: str,
    report: "ReportCollector",
    include_details: bool = True,
) -> tuple[int, int]:
    """
    Translate the output of `validate_table_core` into `ReportCollector` entries.

    Intentionally free of Streamlit imports. Callers that provide their own
    detailed column rendering (e.g. `validate_table` in this module, which uses
    `render_missing_columns` / `render_invalid_values`) should pass
    `include_details=False` to suppress the plain-text detail bullets.

    Parameters
    ----------
    result : dict
        Return value of `validate_table_core`.
    table_name : str
        Table name used in log messages (e.g. ``"SUBJECT"``).
    report : ReportCollector
        Collector to append messages to.
    include_details : bool
        When `True` (default), append per-column detail bullets for each
        invalid-value entry. Pass `False` when a richer rendering layer
        (e.g. Streamlit widgets) handles the details separately.

    Returns
    -------
    tuple[int, int]
        ``(errors_counter, warnings_counter)`` — counts of blocking errors
        and non-blocking warnings added during this call.
    """
    errors_counter = 0
    warnings_counter = 0

    missing_required  = result["missing_required"]
    missing_optional  = result["missing_optional"]
    all_null_required = result["all_null_required"]
    all_null_optional = result["all_null_optional"]
    null_columns      = result["null_columns"]
    invalid_required  = result["invalid_required"]
    invalid_optional  = result["invalid_optional"]
    invalid_entries   = result["invalid_entries"]
    total_required    = result["total_required"]
    total_optional    = result["total_optional"]

    # --- Missing columns ---
    if missing_required:
        report.add_error(
            f"{emoji_error} -- Missing {len(missing_required)}/{total_required} **required** columns "
            f"in *{table_name}*: {', '.join(missing_required)}"
        )
        errors_counter += len(missing_required)

    if missing_optional:
        report.add_warning(
            f"{emoji_warning} -- Missing {len(missing_optional)}/{total_optional} **optional** columns "
            f"in *{table_name}*: {', '.join(missing_optional)}"
        )
        warnings_counter += len(missing_optional)

    # --- All-null columns ---
    if all_null_required:
        report.add_error(
            f"{emoji_error} -- {len(all_null_required)} **required** columns are completely NULL "
            f"in *{table_name}*: {', '.join(all_null_required)}"
        )
        errors_counter += len(all_null_required)

    if all_null_optional:
        report.add_warning(
            f"{emoji_warning} -- {len(all_null_optional)} **optional** columns are completely NULL "
            f"in *{table_name}*: {', '.join(all_null_optional)}"
        )
        warnings_counter += len(all_null_optional)

    # --- Success: all columns present and non-null ---
    if not missing_required and not all_null_required:
        report.add_success(
            f"{emoji_success} -- All {total_required} **required** columns present with data in *{table_name}*"
        )

    if not missing_optional and not all_null_optional:
        report.add_success(
            f"{emoji_success} -- All {total_optional} **optional** columns present with data in *{table_name}*"
        )

    # --- Partial nulls ---
    for _opt_req, column, count in null_columns:
        report.add_warning(f"{emoji_warning} -- column _**{column}**_ has {count} empty values")
        warnings_counter += 1

    if not null_columns:
        report.add_success(f"{emoji_success} -- No columns with partial empty values were found")

    # --- Invalid values ---
    if invalid_required:
        report.add_error(
            f"{emoji_error} -- {len(invalid_required)} **required** columns with invalid values "
            f"in *{table_name}*: {', '.join(invalid_required)}"
        )
        errors_counter += len(invalid_required)
    else:
        report.add_success(f"{emoji_success} -- No invalid values in required columns")

    if invalid_optional:
        report.add_warning(
            f"{emoji_warning} -- {len(invalid_optional)} **optional** columns with invalid values "
            f"in *{table_name}*: {', '.join(invalid_optional)}"
        )
        warnings_counter += len(invalid_optional)
    else:
        report.add_success(f"{emoji_success} -- No invalid values in optional columns")

    # --- Detailed invalid entries (opt-in) ---
    if include_details and invalid_entries:
        report.add_markdown("**Details of invalid values by column:**")
        for opt_req, column, n_invalid, valid_descr, invalid_descr in invalid_entries:
            column_type = opt_req.capitalize()
            bullet = (
                f"- **{column_type}** column `{column}` has {n_invalid} invalid values:\n"
                f"  - **Invalid values:** {invalid_descr}\n"
                f"  - **Expected:** {valid_descr}"
            )
            report.add_markdown(bullet)

    return errors_counter, warnings_counter


def validate_table(df_after_fill: pd.DataFrame, table_name: str,
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
            Table after filling out missing columns with `NULL_SENTINEL`.
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

    result = validate_table_core(df_after_fill, cde_rules)

    # Compose summary report; per-column details rendered below as Streamlit widgets
    errors_counter, warnings_counter = compose_validation_report(
        result, table_name, validation_report, include_details=False
    )

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

def get_invalid_status_rows(
        df_with_status: pd.DataFrame,
        column_with_status: str,
        expected_status: str,
        transient_statuses: list[str]):
    """
    Given a DataFrame with a column_with_status, return three DataFrames:
    1) Rows where column_with_status does not start with expected_status
    2) Rows where column_with_status is in transient_statuses
    3) Rows where column_with_status is neither expected_status nor in transient_statuses

    Parameters
    ----------
    df_with_status: pd.DataFrame
        DataFrame containing a column_with_status with status values.
    column_with_status: str
        Name of the column containing status values.
    expected_status: str
        The expected valid startwith(expected_status) (e.g., "Ok: ").
    transient_statuses: list[str]
        List of transient status values (e.g., ["Loading...", ""]).

    Returns
    -------
    invalid_rows: pd.DataFrame
        Rows where the value of column_with_status does not start with expected_status.
    transient_rows: pd.DataFrame
        Rows where the value of column_with_status is in transient_statuses.
    hard_invalid_rows: pd.DataFrame
        Rows where the value of column_with_status is neither expected_status nor in transient_statuses.
    """

    status_series = (
        df_with_status[column_with_status]
        .fillna("")
        .astype(str)
        .str.strip()
    )
    invalid_rows = df_with_status[~status_series.str.startswith(expected_status)]
    transient_rows = df_with_status[status_series.isin(transient_statuses)]
    hard_invalid_rows = df_with_status[
        (~status_series.str.startswith(expected_status)) & (~status_series.isin(transient_statuses))
    ]
    return invalid_rows, transient_rows, hard_invalid_rows

def read_valid_categories_with_status_retry(
        load_df_with_status_fn: callable,
        max_tries: int,
        sleep_seconds: int,
        expected_status: str,
        column_with_status: str,
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
        The expected valid startwith(expected_status) value.
    transient_statuses: list[str]
        List of transient status values.

    Returns
    -------
    pd.DataFrame
        The DataFrame with column 'Status' after retries.
    """

    for attempt_index in range(1, max_tries + 1):
        last_df = load_df_with_status_fn()
        invalid_rows, transient_rows, hard_invalid_rows = get_invalid_status_rows(last_df, column_with_status, expected_status, transient_statuses)

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
