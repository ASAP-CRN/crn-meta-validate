import pandas as pd

# Canonical sentinel used in sanitized CSVs for null-like entries
NULL_SENTINEL = "NA"

# Textual representations that should be normalized to the sentinel when cleaning
_NULL_LIKE_STRINGS = {
    "none",
    "None",
    "nan",
    "NaN",
    "NAN",
    "N/A",
    "n/a",
}


def compute_missing_mask(column_series: pd.Series) -> pd.Series:
    """
    Compute a boolean mask indicating missing values in a pandas Series.

    For the purposes of the app's "missing value" workflows, a value is
    considered missing if and only if it is either:

    * a true pandas missing value (pd.NA / NaN), or
    * an empty / whitespace-only string.

    Textual null-like tokens such as 'NA', 'none', or 'nan' are treated as
    regular, non-missing values here so that they are allowed as explicit
    FillNull choices without being re-flagged as missing later on.
    """
    column_as_string = column_series.astype("string")
    is_blank = column_as_string.str.fullmatch(r"\s*")
    return column_as_string.isna() | is_blank


def normalize_null_like_series(column_series: pd.Series, sentinel: str = NULL_SENTINEL) -> pd.Series:
    """
    Normalize empty and textual null-like values in a Series to a single sentinel string.

    This is used when producing sanitized CSVs and for downstream validation
    that expects a uniform placeholder for null-like entries.
    """
    column_as_string = column_series.astype("string")

    # Normalize true NA values and whitespace-only strings
    is_blank = column_as_string.str.fullmatch(r"\s*")
    column_as_string = column_as_string.mask(is_blank, sentinel)
    column_as_string = column_as_string.fillna(sentinel)

    # Normalize configured textual null-like tokens
    if _NULL_LIKE_STRINGS:
        mapping = {token: sentinel for token in _NULL_LIKE_STRINGS}
        column_as_string = column_as_string.replace(mapping)

    return column_as_string


def normalize_null_like_dataframe(dataframe: pd.DataFrame, sentinel: str = NULL_SENTINEL) -> pd.DataFrame:
    """
    Return a copy of *dataframe* where all empty / null-like entries have
    been normalized to *sentinel*.
    """
    normalized = dataframe.copy()
    for column_name in normalized.columns:
        normalized[column_name] = normalize_null_like_series(
            normalized[column_name],
            sentinel=sentinel,
        )
    return normalized


def table_has_missing_values(dataframe: pd.DataFrame) -> bool:
    """
    Determine whether a DataFrame contains missing values using the
    same logic as compute_missing_mask().
    """
    for column_name in dataframe.columns:
        column_series = dataframe[column_name]
        missing_mask = compute_missing_mask(column_series)
        if bool(missing_mask.any()):
            return True

    return False


def tables_with_missing_values(input_dataframes_dic: dict) -> list:
    """
    Return a list of table names that contain missing values,
    based on compute_missing_mask().
    """
    tables_with_missing_values_ls = []

    for table_name, dataframe in input_dataframes_dic.items():
        if table_has_missing_values(dataframe):
            tables_with_missing_values_ls.append(table_name)

    return tables_with_missing_values_ls
