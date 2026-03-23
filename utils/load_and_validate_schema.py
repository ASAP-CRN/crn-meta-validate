"""
load_and_validate_schema.py — Schema and CDE bootstrap for the ASAP CRN metadata QC app.

Loads the app-schema JSON and the CDE ValidCategories Google Spreadsheet, returning
all variables required by downstream steps in the application.

This module is intentionally free of Streamlit imports so it can be used by other
repositories that do not run inside a Streamlit context. Error handling therefore
raises ``RuntimeError`` / ``ValueError`` directly instead of calling ``st.error`` /
``st.stop()``.

Typical usage (as done in app.py)::

    from utils.load_and_validate_schema import load_and_validate_schema

    schema_config = load_and_validate_schema(
        repo_root=repo_root,
        webapp_version=webapp_version,
    )

The returned :class:`SchemaConfig` dataclass exposes every variable that was
previously defined at module-level in ``app.py`` between lines 123–180.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Dict, List, Optional, Set

from utils.cde import read_ValidCategories
from utils.help_menus import ensure_step1_other_options


# ---------------------------------------------------------------------------
# Public return type
# ---------------------------------------------------------------------------

@dataclass
class SchemaConfig:
    """All schema-derived values needed by the rest of the application.

    Attributes
    ----------
    # --- App schema ---
    app_schema : dict
        Raw parsed content of resource/app_schema_{webapp_version}.json.
    version_display : str
        Human-readable version string for the UI (e.g. "Web app v0.9.2 - CDE v4.2").
    default_delimiter : str
        Default CSV/TSV input delimiter (e.g. ",").

    # --- CDE version ---
    cde_version : str
        Primary CDE version string (e.g. "v4.2").
    old_cde_version : Optional[str]
        Legacy CDE version string when 'allow_old_cde' is enabled, else None.
    allow_old_cde : bool
        Whether the UI should offer a toggle to validate against the old CDE version.
    cde_mandatory_fields : List[str]
        CDE columns that must be non-null after loading (e.g., "Table", "Field", "DisplayName").

    # --- Google Sheets URLs and IDs ---
    cde_spreadsheet_id : str
        Google Spreadsheet ID for the CDE workbook.
    cde_current_id : str
        Sheet GID for the 'CDE_current' tab (used in help-menu links).
    cde_url_base : str
        Base URL for the CDE Google Spreadsheet.
    cde_google_sheet : str
        Direct CSV-export URL for the primary CDE version tab.
    cde_google_sheet_current : str
        Edit URL for the 'CDE_current' tab (used in help-menu links).
    old_cde_google_sheet : Optional[str]
        Direct CSV-export URL for the old CDE version tab, or None.
    use_local : bool
        If 'True' load CDE/ValidCategories from local resource files instead of Google Sheets.

    # --- Validation variables ---
    valid_categories_name : str
        Sheet tab name for ValidCategories (always 'ValidCategories').
    valid_categories_sheet : str
        Direct CSV-export URL for the ValidCategories tab.
    valid_categories_mandatory : List[str]
        ValidCategories columns that must be present and non-null (e.g., "Table", "Category", "ValidatorAppKey").
    status_CDE_sync : str
        Column name for CDE-sync status in ValidCategories.
    status_CDE_def : str
        Column name for CDE-assay-defined status in ValidCategories.
    status_AIT : str
        Column name for AIT-sync status in ValidCategories.
    AIT_name : str
        Sheet tab name for AssayInstrumentTechnology (always 'AssayInstrumentTechnology').
    REQUIRED_TABLES : List[str]
        Metadata table names that must be uploaded by the user (e.g., SAMPLE, ASSAY).

    # --- Validated lists, which are shown in the App Step 1 dropdown menus ---
    SPECIES : List[str]
        Species display labels for Step 1 dropdowns (includes 'Other').
    SAMPLE_SOURCE : List[str]
        Sample-source display labels for Step 1 dropdowns (includes 'Other').
    ASSAY_DICT : Dict[str, str]
        Mapping 'ValidatorAppKey' → 'ValidatorAppDisplay' for assays.
    ASSAY_TYPES : List[str]
        Ordered list of assay display labels (includes 'Other').
    ASSAY_LABEL_TO_KEY : Dict[str, str]
        Reverse mapping 'ValidatorAppDisplay' → 'ValidatorAppKey' (includes 'Other').
    ASSAY_KEYS : Set[str]
        Set of all assay keys (includes 'other').
    """

    # --- App schema ---
    app_schema: dict
    version_display: str
    default_delimiter: str

    # --- CDE version ---
    cde_version: str
    old_cde_version: Optional[str]
    allow_old_cde: bool
    cde_mandatory_fields: List[str]

    # --- Google Sheets URLs and IDs ---
    cde_spreadsheet_id: str
    cde_current_id: str
    cde_url_base: str
    cde_google_sheet: str
    cde_google_sheet_current: str
    old_cde_google_sheet: Optional[str]
    use_local: bool

    # --- Validation variables ---
    valid_categories_name: str
    valid_categories_sheet: str
    valid_categories_mandatory: List[str]
    status_CDE_sync: str
    status_CDE_def: str
    status_AIT: str
    AIT_name: str
    REQUIRED_TABLES: List[str]

    # --- Validated lists, which are shown in the App Step 1 dropdown menus ---
    SPECIES: List[str]
    SAMPLE_SOURCE: List[str]
    ASSAY_DICT: Dict[str, str]
    ASSAY_TYPES: List[str]
    ASSAY_LABEL_TO_KEY: Dict[str, str]
    ASSAY_KEYS: Set[str]


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def load_and_validate_schema(
    repo_root: str,
    webapp_version: str,
    use_local: bool = False,
) -> SchemaConfig:
    """Load the app-schema JSON and bootstrap CDE category lists.

    Parameters
    ----------
    repo_root : str
        Absolute path to the repository root directory (i.e. the directory that
        contains ``resource/`` and ``app.py``).
    webapp_version : str
        Version string used to locate ``resource/app_schema_{webapp_version}.json``
        (e.g. ``"v0.9.2"``).
    use_local : bool
        If ``True``, load CDE and ValidCategories data from local resource files
        instead of fetching from Google Sheets. Defaults to ``False``.

    Returns
    -------
    SchemaConfig
        Fully populated configuration dataclass.

    Raises
    ------
    FileNotFoundError
        If the app-schema JSON file does not exist at the expected path.
    ValueError
        If required keys are absent from the app-schema JSON.
    RuntimeError
        If the ValidCategories sheet cannot be loaded or fails status validation.
    """

    # ------------------------------------------------------------------
    # 1. Load and parse app_schema JSON
    # ------------------------------------------------------------------
    app_schema_path = os.path.join(repo_root, "resource", f"app_schema_{webapp_version}.json")
    if not os.path.isfile(app_schema_path):
        raise FileNotFoundError(
            f"App schema not found at expected path: {app_schema_path}"
        )

    with open(app_schema_path, "r") as json_file:
        app_schema = json.load(json_file)

    # ------------------------------------------------------------------
    # 2. Extract configuration values from app_schema
    # ------------------------------------------------------------------
    try:
        cde_version: str = app_schema["cde_definition"]["cde_version"]
        old_cde_version: Optional[str] = app_schema["cde_definition"].get("old_cde_version")
        allow_old_cde: bool = bool(app_schema["cde_definition"].get("allow_old_cde", False))
        cde_spreadsheet_id: str = app_schema["cde_definition"]["spreadsheet_id"]
        cde_current_id: str = app_schema["cde_definition"]["cde_current_sheet_id_for_help"]
        default_delimiter: str = app_schema["default_input_delimiter"]
        REQUIRED_TABLES: List[str] = app_schema["table_names"]["required"]
        cde_mandatory_fields: List[str] = app_schema["cde_definition"]["cde_mandatory_fields"]
        valid_categories_mandatory: List[str] = app_schema["cde_definition"]["valid_categ_mandatory_fields"]
    except KeyError as e:
        raise ValueError(
            f"Required key missing from app_schema JSON ({app_schema_path}): {e}"
        ) from e

    # ------------------------------------------------------------------
    # 3. Build CDE Google Sheets URLs
    # ------------------------------------------------------------------
    valid_categories_name = "ValidCategories"
    AIT_name = "AssayInstrumentTechnology"

    cde_url_base = f"https://docs.google.com/spreadsheets/d/{cde_spreadsheet_id}"
    cde_google_sheet = f"{cde_url_base}/gviz/tq?tqx=out:csv&sheet={cde_version}"
    valid_categories_sheet = f"{cde_url_base}/gviz/tq?tqx=out:csv&sheet={valid_categories_name}"
    cde_google_sheet_current = f"{cde_url_base}/edit?gid={cde_current_id}#gid={cde_current_id}"

    status_CDE_sync = "Status_CDE_sync"
    status_CDE_def = "Status_CDE_assay_defined"
    status_AIT = "Status_AIT_sync"

    old_cde_google_sheet: Optional[str] = None
    if allow_old_cde and old_cde_version:
        old_cde_google_sheet = f"{cde_url_base}/gviz/tq?tqx=out:csv&sheet={old_cde_version}"

    # ------------------------------------------------------------------
    # 4. Load ValidCategories and extract Step 1 dropdown data
    # ------------------------------------------------------------------
    SPECIES, SAMPLE_SOURCE, ASSAY_DICT = read_ValidCategories(
        valid_categories_sheet=valid_categories_sheet,
        valid_categories_name=valid_categories_name,
        valid_categories_mandatory=valid_categories_mandatory,
        status_CDE_sync=status_CDE_sync,
        status_CDE_def=status_CDE_def,
        status_AIT=status_AIT,
        local=use_local,
    )

    ASSAY_TYPES: List[str] = list(ASSAY_DICT.values())
    ASSAY_LABEL_TO_KEY: Dict[str, str] = {label: key for key, label in ASSAY_DICT.items()}
    ASSAY_KEYS: Set[str] = set(ASSAY_DICT.keys())

    # ------------------------------------------------------------------
    # 5. Ensure "Other" is always present in Step 1 dropdowns
    # ------------------------------------------------------------------
    SPECIES, SAMPLE_SOURCE, ASSAY_TYPES, ASSAY_LABEL_TO_KEY, ASSAY_KEYS = ensure_step1_other_options(
        species_options=SPECIES,
        sample_source_options=SAMPLE_SOURCE,
        assay_type_options=ASSAY_TYPES,
        assay_label_to_key=ASSAY_LABEL_TO_KEY,
        assay_keys=ASSAY_KEYS,
    )

    # ------------------------------------------------------------------
    # 6. Build version display string
    # ------------------------------------------------------------------
    version_display = f"Web app {webapp_version} - CDE {cde_version}"

    return SchemaConfig(
        # --- App schema ---
        app_schema=app_schema,
        version_display=version_display,
        default_delimiter=default_delimiter,
        # --- CDE version ---
        cde_version=cde_version,
        old_cde_version=old_cde_version,
        allow_old_cde=allow_old_cde,
        cde_mandatory_fields=cde_mandatory_fields,
        # --- Google Sheets URLs and IDs ---
        cde_spreadsheet_id=cde_spreadsheet_id,
        cde_current_id=cde_current_id,
        cde_url_base=cde_url_base,
        cde_google_sheet=cde_google_sheet,
        cde_google_sheet_current=cde_google_sheet_current,
        old_cde_google_sheet=old_cde_google_sheet,
        use_local=use_local,
        # --- Validation variables ---
        valid_categories_name=valid_categories_name,
        valid_categories_sheet=valid_categories_sheet,
        valid_categories_mandatory=valid_categories_mandatory,
        status_CDE_sync=status_CDE_sync,
        status_CDE_def=status_CDE_def,
        status_AIT=status_AIT,
        AIT_name=AIT_name,
        REQUIRED_TABLES=REQUIRED_TABLES,
        # --- Validated lists, which are shown in the App Step 1 dropdown menus ---
        SPECIES=SPECIES,
        SAMPLE_SOURCE=SAMPLE_SOURCE,
        ASSAY_DICT=ASSAY_DICT,
        ASSAY_TYPES=ASSAY_TYPES,
        ASSAY_LABEL_TO_KEY=ASSAY_LABEL_TO_KEY,
        ASSAY_KEYS=ASSAY_KEYS,
    )
