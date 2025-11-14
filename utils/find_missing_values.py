import pandas as pd

# Helper: compute the mask of cells considered "missing" according to this app rules (not Pandas default)
def compute_missing_mask(column_series: pd.Series) -> pd.Series:
    """
    Compute a boolean mask indicating missing values in a pandas Series.

    Parameters
    ----------
    column_series : pd.Series
        The column to inspect.
    Returns
    -------
    pd.Series
        Boolean Series where True indicates a missing value.
    """
    column_as_string = column_series.astype("string")
    is_blank = column_as_string.str.fullmatch(r"\s*")
    is_null_like = column_as_string.isin(
        ["none", "None", "nan", "NaN", "NAN"],
    )
    return column_as_string.isna() | is_blank | is_null_like

def table_has_missing_values(dataframe: pd.DataFrame) -> bool:
    """
    Determine whether a DataFrame contains missing values using the
    same logic as Streamlit UI (compute_missing_mask).

    Parameters
    ----------
    dataframe : pandas.DataFrame
        The table to inspect.

    Returns
    -------
    bool
        True if the table contains at least one missing value, False otherwise.
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

    Parameters
    ----------
    input_dataframes_dic : dict
        Mapping of table_name → pandas.DataFrame.

    Returns
    -------
    list
        Table names with missing values.
    """
    tables_with_missing_values_ls = []

    for table_name, dataframe in input_dataframes_dic.items():
        if table_has_missing_values(dataframe):
            tables_with_missing_values_ls.append(table_name)

    return tables_with_missing_values_ls