"""
Pure-Python validation utilities for the ASAP CRN metadata QC pipeline.
No Streamlit dependency — safe to import in any Python context.

Public API
----------
validate_table_eval(df_normalised, cde_rules) -> dict
    Field-by-field CDE validation; returns raw result dict.
compose_validation_report(result, table_name, report, include_details) -> (int, int)
    Translates a validate_table_eval result into ReportCollector entries.
ReportCollector
    Collects validation messages; can be serialised to a text file.
"""

import logging
import re
import time
from ast import literal_eval

import pandas as pd

from utils.find_missing_values import NULL_SENTINEL, normalize_null_like_dataframe  # noqa: F401 — re-exported

NULL = NULL_SENTINEL  ## Canonical token used for null-like values in *_sanitized.csv files

emoji_success = "✅"
emoji_error   = "❌"
emoji_warning = "⚠️"


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
    """Grab logged information from the log file."""
    with open(log_file, 'r') as f:
        report_content = f.read()
    return report_content


def columnize(itemlist):
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
        return [val]  # force to list


class ReportCollector:
    """
    Collect and serialise validation messages (markdown, errors, warnings, etc.).

    Messages are stored in `entries` as ``(msg_type, msg)`` tuples and can be
    written to a text file via `write_to_file`. Streamlit rendering is handled
    separately in `utils.validate_ui`.
    """

    def __init__(self):
        self.entries = []
        self.filename = None

    def add_markdown(self, msg):
        self.entries.append(("markdown", msg))

    def add_success(self, msg):
        self.entries.append(("success", msg))

    def add_error(self, msg):
        self.entries.append(("error", msg))

    def add_warning(self, msg):
        self.entries.append(("warning", msg))

    def add_header(self, msg):
        self.entries.append(("header", msg))

    def add_subheader(self, msg):
        self.entries.append(("subheader", msg))

    def add_divider(self):
        self.entries.append(("divider", None))

    def write_to_file(self, filename):
        self.filename = filename
        with open(filename, 'w') as f:
            f.write(self.get_log())

    def get_log(self):
        """Return all collected entries as a plain-text string."""
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
                report_content += 60 * '-' + '\n'

        return "".join(report_content)

    def reset(self):
        self.entries = []
        self.filename = None

    def print_log(self):
        print(self.get_log())


def validate_table_eval(
    df_normalised: pd.DataFrame,
    cde_rules: pd.DataFrame,
) -> dict:
    """
    Field-by-field validation of a normalised metadata table against CDE rules.

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
    Translate the output of `validate_table_eval` into `ReportCollector` entries.

    Callers that provide their own detailed column rendering (e.g. `validate_table_core`
    in `utils.validate_ui`, which uses `render_missing_columns` /
    `render_invalid_values`) should pass `include_details=False` to suppress the
    plain-text detail bullets.

    Parameters
    ----------
    result : dict
        Return value of `validate_table_eval`.
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


def validate_table_core(
    df: pd.DataFrame,
    table_name: str,
    cde_rules: pd.DataFrame,
    report: "ReportCollector | None" = None,
    include_details: bool = True,
) -> dict:
    """
    Validate a preprocessed table against CDE rules.

    Combines `validate_table_eval` and `compose_validation_report` into a
    single call. Safe to use in any Python context — no Streamlit dependency.

    Parameters
    ----------
    df : pd.DataFrame
        Table with null-like values already normalised to `NULL_SENTINEL`.
    table_name : str
        Name of the table (e.g. ``"SUBJECT"``).
    cde_rules : pd.DataFrame
        CDE rules filtered to this table and OSA selection.
    report : ReportCollector or None
        Existing collector to append to; a new one is created when ``None``.
    include_details : bool
        Passed through to `compose_validation_report`. When ``True`` (default),
        per-column invalid-value bullets are appended to the report.

    Returns
    -------
    dict
        report : ReportCollector
            Collector with all validation messages appended.
        errors : int
            Count of blocking errors.
        warnings : int
            Count of non-blocking warnings.
    """
    if report is None:
        report = ReportCollector()

    result = validate_table_eval(df, cde_rules)
    errors, warnings = compose_validation_report(result, table_name, report, include_details)

    return {"report": report, "errors": errors, "warnings": warnings}


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
    df_with_status : pd.DataFrame
        DataFrame containing a column_with_status with status values.
    column_with_status : str
        Name of the column containing status values.
    expected_status : str
        The expected valid startwith(expected_status) (e.g., "Ok: ").
    transient_statuses : list[str]
        List of transient status values (e.g., ["Loading...", ""]).

    Returns
    -------
    invalid_rows : pd.DataFrame
        Rows where the value of column_with_status does not start with expected_status.
    transient_rows : pd.DataFrame
        Rows where the value of column_with_status is in transient_statuses.
    hard_invalid_rows : pd.DataFrame
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
    load_df_with_status_fn : callable
        Function that returns the DataFrame with column 'Status' when called.
    max_tries : int
        Maximum number of attempts to load the DataFrame.
    sleep_seconds : int
        Number of seconds to wait between attempts.
    expected_status : str
        The expected valid startwith(expected_status) value.
    transient_statuses : list[str]
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
