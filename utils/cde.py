"""
CDE (Common Data Elements) loading utilities for ASAP CRN metadata QC app

This module handles loading and processing of CDE definitions from either
Google Sheets or local CSV files.

Applies filtering of CDE rules based on selected species, tissue/cell type and assay type.
"""

import pandas as pd
import streamlit as st
import json
from pathlib import Path
from typing import Tuple, Dict, List

def parse_json_list_cell(cell_value: str) -> List[str]:
    """Parse a JSON-encoded list stored in a CDE cell.

    The CDE stores specificity columns (e.g., SpecificAssays) as strings like:
      - '["amplicon_metagenomics"]'
      - '["Brain","iPSC"]'
    Empty / NaN-like values should be treated as an empty list.
    """
    if cell_value is None:
        return []
    normalized = str(cell_value).strip()
    if normalized == "" or normalized.lower() in {"nan", "none"}:
        return []
    if normalized.startswith("["):
        try:
            parsed = json.loads(normalized)
        except Exception:
            return [normalized]
        if isinstance(parsed, list):
            return [str(item) for item in parsed if str(item).strip() != ""]
        return [str(parsed)]
    return [normalized]

def filter_cde_rules_for_selection(
    cde_dataframe: pd.DataFrame,
    selected_species: str | None = None,
    selected_tissue_cell: str | None = None,
    selected_assay_type: str | None = None,
) -> pd.DataFrame:
    """Filter CDE rows based on SpecificSpecies / SpecificTissueCell / SpecificAssays.

    Semantics:
    - If a Specific* cell is empty, the row applies to all selections for that axis.
    - If it is non-empty, the row applies only if the selection is present in the list.
    - If a selection is None/empty, that axis is not used for filtering.

    Notes:
    - SpecificAssays values are dictionary keys (e.g., 'bulk_rna_seq').
    - SpecificTissueCell and SpecificSpecies values are list elements (e.g., 'Brain', 'Human').
    """
    if cde_dataframe.empty:
        return cde_dataframe

    def _axis_allows(cell_value: str, selected_value: str | None) -> bool:
        if selected_value is None or str(selected_value).strip() == "":
            return True
        allowed_values = parse_json_list_cell(cell_value)
        if len(allowed_values) == 0:
            return True
        return str(selected_value) in set(allowed_values)

    filtered_df = cde_dataframe.copy()

    if "SpecificAssays" in filtered_df.columns:
        filtered_df = filtered_df[
            filtered_df["SpecificAssays"].apply(lambda cell_value: _axis_allows(cell_value, selected_assay_type))
        ]

    if "SpecificTissueCell" in filtered_df.columns:
        filtered_df = filtered_df[
            filtered_df["SpecificTissueCell"].apply(lambda cell_value: _axis_allows(cell_value, selected_tissue_cell))
        ]

    if "SpecificSpecies" in filtered_df.columns:
        filtered_df = filtered_df[
            filtered_df["SpecificSpecies"].apply(lambda cell_value: _axis_allows(cell_value, selected_species))
        ]
    # st.dataframe(filtered_df) ## DEBUGGING: shows filtered CDE for table

    return filtered_df.reset_index(drop=True)

@st.cache_data
def read_CDE(
    cde_version: str,
    cde_google_sheet: str,
    local: bool = False,
    local_filename: str = None,
) -> Tuple[pd.DataFrame, Dict[str, str]]:
    """
    Load CDE (Common Data Elements) and return a dataframe and dictionary of dtypes.
    
    Parameters
    ----------
    cde_version : str
        Version of the CDE to load (e.g., 'v4.0', 'v3.4', etc.)
    cde_google_sheet : str
        URL to the Google Sheets CDE document
    local : bool, optional
        If True, load from local file instead of Google Sheets (default: False)
    local_filename : str, optional
        Name of the local CDE file (without path or extension)
        
    Returns
    -------
    Tuple[pd.DataFrame, Dict[str, str]]
        - CDE dataframe with columns: Table, Field, Description, DataType, Required, Validation, etc.
        - Dictionary mapping table names to their dtypes
        
    Raises
    ------
    Streamlit error and stops execution if CDE cannot be loaded
    """
    
    # Define column list based on CDE version
    # Specificity column headers of Species-, Tissue/Cell-, and Assay-specific values as: SpecificAssays, SpecificTissueCell, SpecificSpecies
    column_list = [
        "Table",
        "Field",
        "DisplayName",
        "Description",
        "DataType",
        "Required",
        "Validation",
        "FillNull",
        "SpecificAssays",
        "SpecificTissueCell",
        "SpecificSpecies",
    ]
    
    # Configuration flags
    include_asap_ids = False
    include_aliases = False
    
    # Determine local filename if not provided
    if local_filename is None:
        local_filename = get_cde_filename(cde_version)
    
    # Load CDE from either local file or Google Sheets
    cde_dataframe = load_cde_data(
        local=local,
        local_filename=local_filename,
        cde_google_sheet=cde_google_sheet,
        cde_version=cde_version,
    )
    
    # Filter and clean the dataframe
    cde_dataframe = clean_cde_dataframe(
        cde_dataframe,
        column_list,
        include_asap_ids,
        include_aliases,
        cde_version,
    )

    # Validate completeness of critical CDE columns
    cde_dataframe = validate_cde_completeness(cde_dataframe)

    # Ensure specificity columns exist for older CDE versions
    for col in ["SpecificAssays", "SpecificTissueCell", "SpecificSpecies"]:
        if col not in cde_dataframe.columns:
            cde_dataframe[col] = pd.NA

    # Create dtype dictionary
    dtype_dict = create_dtype_dict(cde_dataframe)
    
    return cde_dataframe, dtype_dict

def get_cde_filename(cde_version: str) -> str:
    """
    Get the appropriate CDE filename for the given version.
    
    Parameters
    ----------
    cde_version : str
        Version of the CDE
        
    Returns
    -------
    str
        Filename (without extension) for the CDE version
        
    Raises
    ------
    Streamlit error and stops execution if version is unsupported
    """
    if cde_version in ["v1", "v2", "v2.1", "v3.0", "v3.0-beta", "v3.1", "v3.2", "v3.3", "v3.3-beta", "v3.4", "v4.0", "v4.0-beta", "v4.1"]:
        return f"ASAP_CDE_{cde_version}"
    elif cde_version in ["v3", "v3.0.0"]: # defaults to v3.0
        return "ASAP_CDE_v3.0"
    elif cde_version in ["v3.2-beta"]: # defaults to v3.2
        return "ASAP_CDE_v3.2"
    else:
        st.error(f"❌ Unsupported cde_version: {cde_version}")
        st.stop()

def load_cde_data(
    local: bool,
    local_filename: str,
    cde_google_sheet: str,
    cde_version: str,
) -> pd.DataFrame:
    """
    Load CDE data from either local file or Google Sheets.
    
    Parameters
    ----------
    local : bool
        If True, load from local file
    local_filename : str
        Name of the local CDE file
    cde_google_sheet : str
        URL to the Google Sheets CDE document
    cde_version : str
        Version of the CDE
        
    Returns
    -------
    pd.DataFrame
        Raw CDE dataframe
        
    Raises
    ------
    Streamlit error and stops execution if loading fails
    """
    if local:
        root = Path(__file__).parent.parent
        cde_local = root / f"resource/{local_filename}.csv"
        st.info(f"Using CDE {cde_version} from local resource/")
        try:
            return pd.read_csv(cde_local)
        except Exception as try_exception:
            st.error(f"ERROR!!! Could not read CDE from local resource/{cde_local}")
            st.error(f"Error details: {str(try_exception)}")
            st.stop()
    else:
        st.info(f"Using CDE {cde_version} from Google doc")
        try:
            return pd.read_csv(cde_google_sheet)
        except Exception as try_exception:
            st.error(f"ERROR!!! Could not read CDE from Google doc:\n{cde_google_sheet}")
            st.error(f"Error details: {str(try_exception)}")
            st.stop()

def clean_cde_dataframe(
    cde_dataframe: pd.DataFrame,
    column_list: List[str],
    include_asap_ids: bool,
    include_aliases: bool,
    cde_version: str,
) -> pd.DataFrame:
    """
    Clean and filter the CDE dataframe.
    
    Parameters
    ----------
    cde_dataframe : pd.DataFrame
        Raw CDE dataframe
    column_list : List[str]
        List of columns to keep
    include_asap_ids : bool
        Whether to include ASAP IDs
    include_aliases : bool
        Whether to include aliases
    cde_version : str
        Version of the CDE
        
    Returns
    -------
    pd.DataFrame
        Cleaned CDE dataframe
    """
    # Drop ASAP_ids if not requested
    if not include_asap_ids:
        cde_dataframe = cde_dataframe[cde_dataframe["Required"] != "Assigned"]
        cde_dataframe = cde_dataframe.reset_index(drop=True)
    
    # Drop Alias if not requested
    if not include_aliases:
        cde_dataframe = cde_dataframe[cde_dataframe["Required"] != "Alias"]
        cde_dataframe = cde_dataframe.reset_index(drop=True)
    
    # Ensure all requested columns in column_list exist, even if missing in raw CDE
    for required_column_name in column_list:
        if required_column_name not in cde_dataframe.columns:
            cde_dataframe[required_column_name] = pd.NA

    # Select only required columns and drop rows with no table name
    cde_dataframe = cde_dataframe.loc[:, column_list]
    cde_dataframe = cde_dataframe.dropna(subset=["Table"])
    cde_dataframe = cde_dataframe.reset_index(drop=True)
    cde_dataframe = cde_dataframe.drop_duplicates()
    
    return cde_dataframe

def validate_cde_completeness(cde_dataframe: pd.DataFrame) -> pd.DataFrame:
    """Validate that required CDE columns are present and contain no NULL cells.
    Raises a Streamlit error and stops execution if validation fails.
    """
    required_columns = [
        "Table",
        "Field",
        "DisplayName",
        "Description",
        "DataType",
        "Required",
        "FillNull",
    ]

    # Ensure all required columns exist
    for required_column_name in required_columns:
        if required_column_name not in cde_dataframe.columns:
            st.error(
                "ERROR!!! CDE is missing required column '"
                + required_column_name
                + "'. Please fix the CDE spreadsheet and reload the app.",
            )
            st.stop()

    # Ensure there are no NULL/empty values in the required columns
    null_mask = cde_dataframe[required_columns].isna()
    if null_mask.any().any():
        problematic_rows = cde_dataframe[null_mask.any(axis=1)][["Table", "Field"]].copy()
        problematic_rows = problematic_rows.fillna("UNKNOWN")

        field_labels: List[str] = []
        for row_index, row_values in problematic_rows.head(10).iterrows():
            table_value = str(row_values.get("Table", "UNKNOWN"))
            field_value = str(row_values.get("Field", "UNKNOWN"))
            field_labels.append(f"{table_value}.{field_value}")

        extra_count = problematic_rows.shape[0] - len(field_labels)
        details = ", ".join(field_labels)
        if extra_count > 0:
            details = f"{details}, and {extra_count} more"

        st.error(
            "ERROR!!! The CDE spreadsheet has NULL values in required columns. "
            f"{required_columns}. "
            f"Examples: {details}. Please report this bug to [support@dnastack.com](mailto:support@dnastack.com)",
        )
        st.stop()

    return cde_dataframe


def create_dtype_dict(cde_dataframe: pd.DataFrame) -> Dict[str, str]:
    """
    Create a dictionary mapping table names to their dtypes.
    
    Parameters
    ----------
    cde_dataframe : pd.DataFrame
        Cleaned CDE dataframe
        
    Returns
    -------
    Dict[str, str]
        Dictionary mapping table names to 'str' dtype
    """
    table_list = list(cde_dataframe["Table"].unique())
    return {table: "str" for table in table_list}

def get_table_cde(
    cde_dataframe: pd.DataFrame,
    table_name: str,
    selected_species: str | None = None,
    selected_tissue_cell: str | None = None,
    selected_assay_type: str | None = None,
) -> pd.DataFrame:
    """
    Extract CDE rules for a specific table.
    
    Parameters
    ----------
    cde_dataframe : pd.DataFrame
        Full CDE dataframe
    table_name : str
        Name of the table to extract rules for
        
    Returns
    -------
    pd.DataFrame
        CDE rules for the specified table
    """
    table_cde_rules = cde_dataframe[cde_dataframe["Table"] == table_name].reset_index(drop=True)
    return filter_cde_rules_for_selection(
        table_cde_rules,
        selected_species=selected_species,
        selected_tissue_cell=selected_tissue_cell,
        selected_assay_type=selected_assay_type,
    )

def build_cde_meta_by_field(table_cde_rules: pd.DataFrame) -> Dict[str, Dict[str, str]]:
    """Builds a lookup dictionary of CDE metadata by field name.

    This centralizes construction of the CDE metadata mapping so both the UI
    and the fill-choice application logic use the same source of truth.

    Parameters
    ----------
    table_cde_rules : pd.DataFrame
        CDE rules for a specific table (one row per field).

    Returns
    -------
    Dict[str, Dict[str, str]]
        Mapping from field name to a metadata dictionary containing keys such as
        "Description", "DataType", "Validation", and "FillNull".
    """
    cde_meta_by_field: Dict[str, Dict[str, str]] = {}
    for row_index, cde_row in table_cde_rules.iterrows():
        field_name = cde_row["Field"]
        cde_meta_by_field[field_name] = {
            "Description": cde_row.get("Description", ""),
            "DataType": cde_row.get("DataType", ""),
            "Validation": cde_row.get("Validation", ""),
            "FillNull": cde_row.get("FillNull", ""),
        }
    return cde_meta_by_field
