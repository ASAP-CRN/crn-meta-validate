"""
ASAP CRN metadata quality control (QC) app

GitHub repository:
https://github.com/ASAP-CRN/crn-meta-validate

Web app production version: https://asap-meta-qc.streamlit.app/
Web app staging version: https://asap-crn-crn-meta-validate-app-update-streamlit-newmodal-m1gdf4.streamlit.app/
Example *csv infiles: https://github.com/ASAP-CRN/crn-meta-validate/tree/Update_Streamlit_NewModalties_and_UX/resource/tester_files

Webapp v0.2 (CDE version v2), 20 August 2023
Webapp v0.3 (CDE version v3), 01 April 2025
Webapp v0.4 (CDE version v3.3-beta), 13 November 2025

Version notes:
Webapp v0.4:
* CDE version is provided in resource/app_schema_{webapp_version}.json and loaded via utils/cde.py
* Added supported species, modality and tissue/cell source dropdowns to select expected tables
* Added reset button to sidebar, reset cache and file uploader
* Added app_schema to manage app configuration
* Added Classes for DelimiterHandler and ProcessedDataLoader to utils/
* Improved delimiter detection and handling logic
* Improved file upload handling and status display

Webapp v0.5:
* Assit users to fillout missing values on each column via radio buttons, free text or dropdown menus
* Improved missing-values detection logic in utils/find_missing_values.py
* Comparison of each column vs. CDE using both Validation and FillNull (newly added in v0.5)
* Adds download button for pre-CDE-validated sanitized CSV

Authors:
- [Andy Henrie](https://github.com/ergonyc)
- [Javier Diaz](https://github.com/jdime)

Contributors:
- [Alejandro Marinez](https://github.com/AMCalejandro)

"""

################################
#### Imports
################################
import json
import pandas as pd
import html
import streamlit as st
import ast
from pathlib import Path
import os, sys
import re
import time
from io import StringIO
from utils.validate import validate_table, ReportCollector, get_extra_columns_not_in_cde
from utils.cde import read_CDE, get_table_cde
from utils.delimiter_handler import DelimiterHandler
from utils.processed_data_loader import ProcessedDataLoader
from utils.find_missing_values import compute_missing_mask, table_has_missing_values, tables_with_missing_values
from utils.help_menus import CustomMenu

webapp_version = "v0.5"

repo_root = str(Path(__file__).resolve().parents[0]) ## repo root

################################
#### Load app schema from JSON
################################
app_schema_path = os.path.join(repo_root, "resource", f"app_schema_{webapp_version}.json")
with open(app_schema_path, "r") as json_file:
    app_schema = json.load(json_file)

# Extract configuration from app_schema
cde_version = app_schema['cde_definition']['cde_version']
cde_spreadsheet_id = app_schema['cde_definition']['spreadsheet_id']
cde_google_sheet = f"https://docs.google.com/spreadsheets/d/{cde_spreadsheet_id}/gviz/tq?tqx=out:csv&sheet={cde_version}" # CDE version set in app_schema and used for validations.
cde_google_sheet_current = f"https://docs.google.com/spreadsheets/d/{cde_spreadsheet_id}/edit?gid=43504703#gid=43504703" # CDE_current tab. We need to use a gid, not a sheet name, in the URL to open the Google Sheet in a browser.
use_local = False  # Set to False to use Google Sheets

# Extract table categories
SPECIES = app_schema['table_categories']['species']
TISSUES_OR_CELLS = app_schema['table_categories']['tissues_or_cells']
MODALITIES = app_schema['table_categories']['modalities']

# Extract required table names
REQUIRED_TABLES = app_schema['table_names']['required']

# Version display for UI
version_display = f"Web app {webapp_version} - CDE {cde_version}"

################################
#### App Setup
################################

st.set_page_config(
    page_title=f"{app_schema['kebab_menu']['page_header']}",
    page_icon="✅",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "Get help": f"{app_schema['kebab_menu']['get_help_url']}",
        "About": f"ASAP CRN {version_display}",
    },
)

def load_css(file_name):
   with open(file_name) as f:
      st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

################################
#### Run a table and return results
################################

@st.cache_data
def setup_report_data(
    report_data_dict: dict, selected_table: str, input_dataframes_dict: dict, cde_dataframe: pd.DataFrame
):
    submit_table_df = input_dataframes_dict[selected_table]
    table_specific_cde = get_table_cde(cde_dataframe, selected_table)
    table_data = (submit_table_df, table_specific_cde)
    report_data_dict[selected_table] = table_data
    return report_data_dict

################################
#### Main app
################################

def main():
    # Initialize file uploader key in session state
    if 'file_uploader_key' not in st.session_state:
        st.session_state.file_uploader_key = 0

    # Provide template
    st.markdown(f'<p class="big-font">ASAP CRN metadata quality control (QC) app {webapp_version}</p>', unsafe_allow_html=True)
    st.markdown(
        f"""
        This app assists ASAP CRN data contributors to QC their metadata tables (e.g. STUDY.csv, SAMPLE.csv, 
        PROTOCOL.csv, etc.) before uploading them to ASAP CRN Google buckets.
        
        We do this in three steps:     
        **Step 1.** Set up your run, indicate type of dataset to determine expected tables and columns and upload your files.     
        **Step 2.** The app will help to fix common issues, like non-comma delimiters and missing values.     
        **Step 3.** The app reports missing columns and value mismatches vs.
        the [ASAP CRN Common Data Elements (CDE) {cde_version}]({cde_google_sheet_current}).

        Two types of issues will be reported:
        - **Errors**: Must be **fixed by the data contributors** before uploading metadata to ASAP CRN Google buckets.
        - **Warnings**: Recommended to be fixed before uploading, but not required.

        We are [here]({app_schema['kebab_menu']['get_help_url']}) to help if you have questions!     
        Example *csv infiles can be downloaded from [here]({app_schema['example_input_files_url']}).
        

        """,
        unsafe_allow_html=True,
    )

    ############
    ### Step 1: Set up your run and upload files
    ############
    st.markdown("---")
    st.markdown("## Step 1: Set up your run and upload csv files")

    ############
    ### Load CSS (text size, colors, etc.)
    load_css(os.path.join(repo_root, "css", "css.css"))
    
    ############
    ### Render custom menu (replaces hamburger menu)
    custom_menu = CustomMenu(help_url=app_schema['kebab_menu']['get_help_url'])
    custom_menu.render()

    ############
    #### Set dropdown menus for run settings
    col1, col2, col3 = st.columns(3)

    # Drop down menu to select species
    # Currently, it includes both species and tissue/cell source. Will separate later.
    with col1:
        st.markdown('<h3 style="font-size: 25px;">Choose dataset species <span style="color: red;">*</span></h3>',
            unsafe_allow_html=True)
        species = st.selectbox(
            "Dataset species",
            SPECIES,
            label_visibility="collapsed",
            index=None
        )

    # Drop down menu to select tissue/cell source
    with col2:
        st.markdown('<h3 style="font-size: 25px;">Choose tissue/cell <span style="color: red;">*</span></h3>',
                    unsafe_allow_html=True)
        tissue_or_cell = st.selectbox(
            "Tissue or cell source",
            TISSUES_OR_CELLS,
            label_visibility="collapsed",
            index=None
        )

    # Drop down menu to select modality
    with col3:
        st.markdown('<h3 style="font-size: 25px;">Choose modality <span style="color: red;">*</span></h3>',
                    unsafe_allow_html=True)
        modality = st.selectbox(
            "Modality",
            MODALITIES,
            label_visibility="collapsed",
            index=None
        )

    ############
    #### Determine expected tables based on species, tissue/cell source and modality
    table_list = []
    species_success = False
    tissue_or_cell_success = False
    modality_success = False

    table_list = REQUIRED_TABLES.copy()

    if species in SPECIES:
        species_success = True
        species_specific_table_key = re.sub(r'\s+', '_', f"{species.lower()}_specific")
        table_list.extend(app_schema['table_names'][species_specific_table_key])

        if tissue_or_cell in TISSUES_OR_CELLS:
            tissue_or_cell_success = True
            if tissue_or_cell in ["iPSC", "Cell lines"]:
                table_list.extend(["CELL"])
            elif tissue_or_cell in ["Post-mortem brain"]:
                table_list.extend(["PMDBS"])

            if modality in MODALITIES:
                modality_success = True
                if modality in ["Single cell/nucleus RNA-seq", "Bulk RNAseq", "ATAC-seq"]:
                    table_list.extend(["ASSAY_RNAseq"])
                elif modality in ["Spatial transcriptomics"]:
                    table_list.extend(["SPATIAL"])
                elif modality in ["MS Proteomics", "Other MS -omics"]:
                    table_list.extend(["PROTEOMICS"])
                elif modality in ["MULTI-Seq", "Multimodal Seq", "Multiome", "Genetics", "Metagenome", "Other"]:
                    pass

    ############
    #### Pause until user selects species_success and modality_success
    if not species_success or not tissue_or_cell_success or not modality_success:
        st.info("Please select Species, Tissue/Cell, and Modality of your dataset")
        st.stop()

    ############
    #### Print expected tables and load data files
    if len(table_list) > 0:
        table_list_formatted = ", ".join([f"{t}.csv" for t in table_list])
    else:
        st.error("No expected tables found for the selected dataset source and type")
        st.stop()

    ############
    #### Load CDE
    cde_dataframe, dtype_dict = read_CDE(
        cde_version=cde_version,
        cde_google_sheet=cde_google_sheet,
        local=use_local,
    )

    ############
    #### Provide left-side bar for file upload and app reset
    st.sidebar.title("Upload files to validate")
    
    data_files = st.sidebar.file_uploader(
        f"Expected files: \n{table_list_formatted}",
        type=["csv"],
        accept_multiple_files=True,
        key=f"file_uploader_{st.session_state.file_uploader_key}"
    )

    ############
    #### Add Reset button and version info to sidebar (ALWAYS VISIBLE)
    st.sidebar.markdown("---")

    st.markdown("""
                <style>
                div.stButton > button[kind="primary"] {
                border: 2px solid #1f77b4 !important;
                }
                </style>
                """, unsafe_allow_html=True)

    if st.sidebar.button("🔄 Reset App", use_container_width=True, type="primary"):
        # Clear all caches
        st.cache_data.clear()
        st.cache_resource.clear()

        # Fully reset Streamlit session state
        st.session_state.clear()

        # IMPORTANT: reinitialize file_uploader_key with a new unique value
        # so the file uploader widget is rebuilt and does not retain old files
        import time as _reset_time_module
        st.session_state.file_uploader_key = int(_reset_time_module.time() * 1000)

        st.rerun()

    ############
    ### Step 2: Fix common issues (non-comma delimiters and missing values)
    ############
    #### Pause if no files loaded for CDE validation
    if not data_files:
        st.stop()
    else:
        st.markdown("---")
        st.markdown("## Step 2: Fix common issues (non-comma delimiters and missing values)")

    ############
    #### Initialize Delimiter Handler
    delimiter_handler = DelimiterHandler()

    ############
    #### Detect file changes and clear processed state if files have changed
    if data_files:
        # Create a unique identifier for current uploaded files
        current_files_signature = tuple(sorted(f"{f.name}_{f.size}" for f in data_files))
        previous_signature = st.session_state.get("uploaded_files_signature")
        
        if previous_signature != current_files_signature:
            # Files have changed, clear processed state and decisions
            st.session_state["uploaded_files_signature"] = current_files_signature
            st.session_state.pop("files_ready_for_validation", None)
            # Note: We don't clear delimiter_decisions here as they will be repopulated

    ############
    #### Evaluate which files can be validated with CDE rules
    #### For example, files with headers but no data rows will be flagged as invalid and wont be send to CDE evaluation.
    if data_files is None or len(data_files) == 0:
        tables_loaded = False
    elif len(data_files) > 0:
        # Check delimiter decisions BEFORE calling cached load_data()
        # This prevents Streamlit widgets from being inside cached functions
        if not delimiter_handler.check_delimiter_decisions(data_files):
            # Waiting for user to make delimiter decisions
            st.stop()
        
        # Get valid files only (exclude invalid files)
        valid_files = [f for f in data_files if not delimiter_handler.is_file_invalid(f.name, f.size)]
        invalid_files = [f for f in data_files if delimiter_handler.is_file_invalid(f.name, f.size)]
        
        if len(valid_files) == 0:
            st.error("All uploaded files are invalid. Please upload valid CSV files with data rows.")
            st.stop()
        
        # Show file count with status
        if len(invalid_files) > 0:
            st.sidebar.warning(f"N={len(valid_files)} valid files | {len(invalid_files)} invalid files")
        else:
            st.sidebar.success(f"N={len(valid_files)} files loaded")
        
        ############
        #### Button to Apply delimiter decisions
        processed_files = st.session_state.get("files_ready_for_validation")
        if not processed_files:
            # Show the Apply button and wait for user action
            with st.container(border=True):
                # st.markdown("#### Apply your delimiter decisions")
                left_col, right_col = st.columns([1, 2])
                with left_col:
                    if st.button("✅ Apply delimiter decisions and continue", key="apply_delims"):
                        _processed = delimiter_handler.apply_decisions(valid_files)
                        st.session_state["files_ready_for_validation"] = _processed
                        st.success(f"Prepared {len(_processed)} file(s) for validation.")
                        st.rerun()
                with right_col:
                    try:
                        status_str = delimiter_handler.get_file_status_display(data_files)
                        st.markdown(
                            f"<p style='font-size:18px; color:gray;'>File status: {status_str}</p>",
                            unsafe_allow_html=True,
                        )
                    except Exception:
                        pass
            # Stop here and wait for the button to be clicked
            st.stop()

        ############
        #### Process valid files
        loader = ProcessedDataLoader()
        table_names, input_dataframes_dic, file_warnings, row_counts = loader.load(processed_files)
        missing_tables_ls = tables_with_missing_values(input_dataframes_dic)

        # Surface per-file warnings in the UI
        for filename, warnings_list in file_warnings.items():
            for warning_text in warnings_list:
                st.warning(f"**{filename}** — {warning_text}")

        # Files ready for CDE validation
        for table_name in table_names:
            current_row_count = row_counts.get(table_name, 0)
            st.success(f"**{table_name}** ({current_row_count} rows) — Loaded and ready for validation of columns and values.")

        tables_loaded = True
        validation_report_dic = dict()

        ############
        #### Left-side menu logic for uploaded files
        # Log files for CDE validation
        if len(valid_files) > 0:
            st.sidebar.markdown("**Valid files:**")

        for data_file in valid_files:
            file_key = delimiter_handler.get_file_key(data_file.name, data_file.size)
            file_content = data_file.getvalue()
            detected_delimiter, confidence, preview_df = delimiter_handler.detect_delimiter(
                file_content,
                data_file.name,
            )
            delimiter_name = delimiter_handler.get_delimiter_name(detected_delimiter)

            # Look up the user's delimiter decision if it exists; otherwise default to 'keep'
            decisions = st.session_state.get('delimiter_decisions', {})
            decision = decisions.get(file_key)
            if isinstance(decision, dict):
                action = decision.get('action')
            elif isinstance(decision, str):
                action = decision
            else:
                action = 'keep'

            if action == 'convert':
                st.sidebar.success(
                    f"✓ {data_file.name} converted from {delimiter_name} to comma"
                )
            else:
                st.sidebar.success(
                    f"✓ {data_file.name} originally {delimiter_name} delimited"
                )

        # Log invalid files (strikethrough)
        if len(invalid_files) > 0:
            st.sidebar.markdown("**Invalid files (skipped):**")
            for data_file in invalid_files:
                st.sidebar.markdown(f"~~{data_file.name}~~ ❌")

    else:
        st.error("Something went wrong with the file upload. Please click 'Reset App', reload the webpage and try again. If issue persists, contact the ASAP CRN team.")
        st.stop()
        tables_loaded = False

    ############
    ### Fillout missing values (if any)
    ############
    if not tables_loaded:
        st.stop()
    st.markdown("---")

    if missing_tables_ls:
        st.markdown(f"### Let's fill out missing values in these tables: {', '.join(missing_tables_ls)}")

    ############
    #### Create file selection dropdown and run CDE validation for each selected file
    #### Add anchor for "Go back to select a file" button
    st.markdown(
        '''
        <h3 id="choose-a-file-to-continue"
            style="font-size: 25px; scroll-margin-top: 80px;">
            Choose a file to continue <span style="color: red;">*</span>
        </h3>
        ''',
        unsafe_allow_html=True,
    )
    selected_table_name = st.selectbox(
        "Table to fill",
        table_names,
        label_visibility="collapsed",
    )

    ############
    #### Per-file preview and missing-value handling options
    # Bump a simple logic version so that old prepared tables are cleared after code changes
    CURRENT_MV_LOGIC_VERSION = "mv_logic_v3"
    if st.session_state.get("missing_value_logic_version") != CURRENT_MV_LOGIC_VERSION:
        st.session_state["missing_value_logic_version"] = CURRENT_MV_LOGIC_VERSION
        if "prepared_tables" in st.session_state:
            del st.session_state["prepared_tables"]

    # If the user switches to a different table in the dropdown, clear any stale prepared table
    last_key = "last_selected_table_for_mv"
    last_selected = st.session_state.get(last_key)
    if last_selected != selected_table_name:
        prepared_tables_state = st.session_state.get("prepared_tables", {})
        if selected_table_name in prepared_tables_state:
            del prepared_tables_state[selected_table_name]
        st.session_state["prepared_tables"] = prepared_tables_state
        st.session_state[last_key] = selected_table_name

    raw_tables_before_fill = st.session_state.get("raw_tables_before_fill", {})
    selected_raw_df = raw_tables_before_fill.get(
        selected_table_name,
        input_dataframes_dic.get(selected_table_name),
    )

    if selected_raw_df is not None:
        st.markdown(
            f'###### Preview _{selected_table_name}_ <u>before</u> filling out missing values',
            unsafe_allow_html=True
        )
        st.dataframe(selected_raw_df.head(10))

        # Initialize per-table missing-value choices in session state
        if "missing_value_choices" not in st.session_state:
            st.session_state["missing_value_choices"] = {}

        missing_value_choices = st.session_state["missing_value_choices"]

        if selected_table_name not in missing_value_choices:
            missing_value_choices[selected_table_name] = {
                "required": {},
                "required_free_text": {},
                "required_enum_choice": {},
                "optional": {},
                "optional_free_text": {},
            }

        table_missing_choices = missing_value_choices[selected_table_name]
        required_column_choices = table_missing_choices.get("required", {})
        required_free_text = table_missing_choices.get("required_free_text", {})
        required_enum_choice = table_missing_choices.get("required_enum_choice", {})
        optional_column_choices = table_missing_choices.get("optional", {})
        optional_free_text = table_missing_choices.get("optional_free_text", {})

        # Determine required vs optional fields for this table from the CDE
        table_cde_rules = get_table_cde(cde_dataframe, selected_table_name)

        # Normalize Required flag; only 'required' is treated as required. 'assigned' is optional.
        required_flag_normalized = table_cde_rules["Required"].astype(str).str.strip().str.lower()
        required_mask = required_flag_normalized == "required"

        required_fields = [
            field_name
            for field_name in table_cde_rules.loc[
                required_mask,
                "Field",
            ].tolist()
            if field_name in selected_raw_df.columns
        ]

        optional_fields = [
            field_name
            for field_name in table_cde_rules.loc[
                ~required_mask,
                "Field",
            ].tolist()
            if field_name in selected_raw_df.columns
        ]

        # Warn about any columns present in the input table but missing from the CDE
        extra_fields = get_extra_columns_not_in_cde(
            selected_table_name,
            selected_raw_df,
            table_cde_rules,
        )
        if extra_fields:
            message = (
                f"Warning!!! the following {len(extra_fields)} columns from {selected_table_name} "
                "couldn't be found in the CDE and will not be evaluated:\n\n"
                + ", ".join(extra_fields)
            )
            st.warning(message, icon="⚠️")

        # Build lookup for CDE metadata per field (Description, DataType, Validation)
        cde_meta_by_field = {}
        for _, cde_row in table_cde_rules.iterrows():
            field_name = cde_row["Field"]
            cde_meta_by_field[field_name] = {
                "Description": cde_row.get("Description", ""),
                "DataType": cde_row.get("DataType", ""),
                "Validation": cde_row.get("Validation", ""),
                "FillNull": cde_row.get("FillNull", ""),
            }

        # Required columns: one choice per column with missing values
        required_columns_with_missing = []

        for field_name in required_fields:
            column_series = selected_raw_df[field_name]
            missing_mask = compute_missing_mask(column_series)
            missing_count = int(missing_mask.sum())
            if missing_count > 0:
                required_columns_with_missing.append((field_name, missing_count))

        if len(required_columns_with_missing) > 0:
            st.markdown(f"#### Missing values in _{selected_table_name}_ required columns")

            for field_name, missing_count in required_columns_with_missing:
                field_meta = cde_meta_by_field.get(field_name, {})
                description_text = str(field_meta.get("Description", "") or "").strip()
                datatype_text = str(field_meta.get("DataType", "") or "").strip()
                validation_text = str(field_meta.get("Validation", "") or "").strip()
                fillnull_text = str(field_meta.get("FillNull", "") or "").strip()

                # Determine FillNull-based options, falling back to DataType defaults
                datatype_lower = datatype_text.lower()
                option_labels: list[str] = []

                # Parse FillNull from the CDE (list or single value)
                fillnull_values = []
                if fillnull_text:
                    try:
                        parsed_fillnull = ast.literal_eval(fillnull_text)
                        if isinstance(parsed_fillnull, (list, tuple)):
                            fillnull_values = [str(value) for value in parsed_fillnull]
                        else:
                            fillnull_values = [str(parsed_fillnull)]
                    except Exception:
                        fillnull_values = [fillnull_text]

                if fillnull_values:
                    for fill_value in fillnull_values:
                        option_labels.append(f'Fill out with "{fill_value}"')
                else:
                    # Fallback to DataType-based options if FillNull is not defined
                    if datatype_lower in ("integer", "float"):
                        option_labels = [
                            "Fill out with N/A",
                            "Fill out with 0",
                        ]
                    elif "enum" in datatype_lower:
                        suggested_label = "Fill out with first allowed value from Validation"
                        option_labels = [
                            suggested_label,
                            'Fill out with "Unknown"',
                            'Fill out with "Other"',
                        ]
                    else:
                        option_labels = [
                            "Fill out with Unknown",
                            "Fill out with NA",
                        ]

                existing_choice = required_column_choices.get(field_name, option_labels[0])

                try:
                    default_index = option_labels.index(existing_choice)
                except ValueError:
                    default_index = 0

                # Hover tooltip for column name: show Description and DataType
                hover_parts = []
                if description_text:
                    hover_parts.append(description_text)
                if datatype_text:
                    hover_parts.append(f"DataType: {datatype_text}")
                hover_text = " | ".join(hover_parts)
                hover_text_escaped = html.escape(hover_text, quote=True)

                st.markdown(
                    f'* <strong>Required</strong> column <span title="{hover_text_escaped}"><strong>{field_name}</strong></span> '
                    f'has {missing_count} empty values. (DataType: {datatype_text})',
                    unsafe_allow_html=True,
                )

                # Radio: FillNull-driven options (or fallback)
                user_choice = st.radio(
                    "Choose how to fill this column:",
                    option_labels,
                    index=default_index,
                    key=f"missing_required_{selected_table_name}_{field_name}",
                )
                required_column_choices[field_name] = user_choice

                # Place free text and Enum dropdown side by side
                free_text_col, enum_dropdown_col = st.columns(2)

                # Free text input (highest priority if provided)
                with free_text_col:
                    existing_free_text = required_free_text.get(field_name, "")
                    free_text_value = st.text_input(
                        "Free text (optional):",
                        value=existing_free_text,
                        key=f"free_text_{selected_table_name}_{field_name}",
                    )
                    required_free_text[field_name] = free_text_value

                # Enum dropdown (Validation values) for Enum DataType
                with enum_dropdown_col:
                    existing_enum_choice = required_enum_choice.get(field_name, "")

                    if "enum" in datatype_lower and validation_text:
                        validation_values = []
                        try:
                            parsed_validation = ast.literal_eval(validation_text)
                            if isinstance(parsed_validation, (list, tuple)):
                                validation_values = [str(value) for value in parsed_validation]
                        except Exception:
                            validation_values = []

                        if validation_values:
                            dropdown_options = ["(no selection)"] + validation_values
                            try:
                                default_enum_index = dropdown_options.index(existing_enum_choice)
                            except ValueError:
                                default_enum_index = 0

                            selected_enum_value = st.selectbox(
                                "Choose a CDE Validation value to fill (optional):",
                                dropdown_options,
                                index=default_enum_index,
                                key=f"enum_dropdown_{selected_table_name}_{field_name}",
                            )
                            if selected_enum_value == "(no selection)":
                                required_enum_choice[field_name] = ""
                            else:
                                required_enum_choice[field_name] = selected_enum_value
                    else:
                        # Non-Enum columns: ensure we at least preserve any previous enum choice key
                        required_enum_choice[field_name] = required_enum_choice.get(field_name, "")

            table_missing_choices["required"] = required_column_choices
        optional_columns_with_missing = []

        for field_name in optional_fields:
            column_series = selected_raw_df[field_name]
            missing_mask = compute_missing_mask(column_series)
            missing_count = int(missing_mask.sum())
            if missing_count > 0:
                optional_columns_with_missing.append((field_name, missing_count))

        if len(optional_columns_with_missing) > 0:
            st.markdown(f"#### Missing values in _{selected_table_name}_ optional columns")

            for field_name, missing_count in optional_columns_with_missing:
                field_meta = cde_meta_by_field.get(field_name, {})
                description_text = str(field_meta.get("Description", "") or "").strip()
                datatype_text = str(field_meta.get("DataType", "") or "").strip()
                fillnull_text = str(field_meta.get("FillNull", "") or "").strip()

                datatype_lower = datatype_text.lower()

                # Parse FillNull from the CDE (list or single value)
                fillnull_values = []
                if fillnull_text:
                    try:
                        parsed_fillnull = ast.literal_eval(fillnull_text)
                        if isinstance(parsed_fillnull, (list, tuple)):
                            fillnull_values = [str(value) for value in parsed_fillnull]
                        else:
                            fillnull_values = [str(parsed_fillnull)]
                    except Exception:
                        fillnull_values = [fillnull_text]

                option_labels: list[str] = []
                if fillnull_values:
                    for fill_value in fillnull_values:
                        option_labels.append(f'Fill out with "{fill_value}"')
                else:
                    # Fallback to simple defaults if FillNull is not defined
                    option_labels = [
                        "Fill out with Unknown",
                        "Fill out with NA",
                    ]

                existing_choice_opt = optional_column_choices.get(field_name, option_labels[0])
                try:
                    default_opt_index = option_labels.index(existing_choice_opt)
                except ValueError:
                    default_opt_index = 0

                # Hover tooltip for column name: show Description and DataType
                hover_parts_opt = []
                if description_text:
                    hover_parts_opt.append(description_text)
                if datatype_text:
                    hover_parts_opt.append(f"DataType: {datatype_text}")
                hover_text_opt = " | ".join(hover_parts_opt)
                hover_text_opt_escaped = html.escape(hover_text_opt, quote=True)

                st.markdown(
                    f'* <strong>Optional</strong> column <span title="{hover_text_opt_escaped}"><strong>{field_name}</strong></span> '
                    f'has {missing_count} empty values. (DataType: {datatype_text})',
                    unsafe_allow_html=True,
                )

                user_choice_opt = st.radio(
                    "Choose how to fill this optional column:",
                    option_labels,
                    index=default_opt_index,
                    key=f"missing_optional_{selected_table_name}_{field_name}",
                )
                optional_column_choices[field_name] = user_choice_opt

                # Place optional free text in the left half of the row
                free_text_col_opt, spacer_col_opt = st.columns(2)

                # Free text for optional column (highest priority if provided)
                with free_text_col_opt:
                    existing_free_text_opt = optional_free_text.get(field_name, "")
                    free_text_value_opt = st.text_input(
                        "Free text (optional):",
                        value=existing_free_text_opt,
                        key=f"free_text_optional_{selected_table_name}_{field_name}",
                    )
                    optional_free_text[field_name] = free_text_value_opt

        # Persist choices back to session state
        table_missing_choices["required"] = required_column_choices
        table_missing_choices["required_free_text"] = required_free_text
        table_missing_choices["required_enum_choice"] = required_enum_choice
        table_missing_choices["optional"] = optional_column_choices
        table_missing_choices["optional_free_text"] = optional_free_text

        missing_value_choices[selected_table_name] = table_missing_choices
        st.session_state["missing_value_choices"] = missing_value_choices

    else:
        st.info(
            "No preview available for this file. It may not have passed the loading step correctly.",
        )

    if (len(required_columns_with_missing) > 0) or (len(optional_columns_with_missing) > 0):
        ############
        #### Apply missing-value rules first, then preview, then compare vs. CDE
        apply_label = "✅ Apply missing-value choices"
        apply_clicked = st.button(apply_label, key=f"apply_missing_{selected_table_name}")
    else:
        st.info(f"No missing values detected in _{selected_table_name}_. You can proceed to Step 3.")
        apply_clicked = True  # No columns with missing values, so treat as clicked

    if apply_clicked:
        # Compute a prepared DataFrame with the current choices and store it
        effective_raw_df = raw_tables_before_fill.get(
            selected_table_name,
            input_dataframes_dic.get(selected_table_name),
        )

        if effective_raw_df is None:
            st.error("Could not load data for this table. Please go back to the upload step and try again.")
        else:
            table_missing_choices = st.session_state.get("missing_value_choices", {}).get(
                selected_table_name,
                {
                    "required": {},
                    "required_free_text": {},
                    "required_enum_choice": {},
                    "optional": {},
                    "optional_free_text": {},
                },
            )
            required_column_choices = table_missing_choices.get("required", {})
            required_free_text = table_missing_choices.get("required_free_text", {})
            required_enum_choice = table_missing_choices.get("required_enum_choice", {})
            optional_column_choices = table_missing_choices.get("optional", {})
            optional_free_text = table_missing_choices.get("optional_free_text", {})

            prepared_df = effective_raw_df.copy()
            table_cde_rules = get_table_cde(cde_dataframe, selected_table_name)

            # Normalize Required flag; only 'required' is treated as required. 'assigned' is optional.
            required_flag_normalized = table_cde_rules["Required"].astype(str).str.strip().str.lower()
            required_mask = required_flag_normalized == "required"

            required_fields = [
                field_name
                for field_name in table_cde_rules.loc[
                    required_mask,
                    "Field",
                ].tolist()
                if field_name in prepared_df.columns
            ]

            optional_fields = [
                field_name
                for field_name in table_cde_rules.loc[
                    ~required_mask,
                    "Field",
                ].tolist()
                if field_name in prepared_df.columns
            ]

            # Helper: apply one of the choices to a column, using DataType and Validation
            def apply_fill_choice(series, user_choice: str, field_meta: dict, override_value: str | None = None):
                datatype_text = str(field_meta.get("DataType", "") or "").strip()
                validation_text = str(field_meta.get("Validation", "") or "").strip()
                fillnull_text = str(field_meta.get("FillNull", "") or "").strip()
                datatype_lower = datatype_text.lower()

                mask = compute_missing_mask(series)
                fill_value = None

                # Highest priority: explicit override (free text or enum dropdown)
                if override_value:
                    fill_value = override_value
                else:
                    # If user_choice was based on a FillNull radio option, extract the actual value
                    if user_choice and user_choice.startswith('Fill out with "') and user_choice.endswith('"'):
                        fill_value = user_choice[len('Fill out with "'): -1]
                    else:
                        # Fallback to original DataType-based semantics
                        if datatype_lower in ("integer", "float"):
                            if user_choice == "Fill out with N/A":
                                fill_value = "N/A"
                            elif user_choice == "Fill out with 0":
                                fill_value = "0"
                        elif "enum" in datatype_lower:
                            # Try to parse Validation as a Python list and use the first allowed value
                            first_allowed = None
                            if validation_text:
                                try:
                                    parsed = ast.literal_eval(validation_text)
                                    if isinstance(parsed, (list, tuple)) and parsed:
                                        first_allowed = str(parsed[0])
                                except Exception:
                                    first_allowed = None

                            if user_choice == "Fill out with first allowed value from Validation" and first_allowed is not None:
                                fill_value = first_allowed
                            elif user_choice == 'Fill out with "Unknown"':
                                fill_value = "Unknown"
                            elif user_choice == 'Fill out with "Other"':
                                fill_value = "Other"
                        else:
                            # Treat everything else as string
                            if user_choice == "Fill out with Unknown":
                                fill_value = "Unknown"
                            elif user_choice == "Fill out with NA":
                                fill_value = "NA"

                if fill_value is None:
                    return series

                return series.mask(mask, fill_value)


            # Build CDE metadata lookup again
            cde_meta_by_field = {}
            for _, cde_row in table_cde_rules.iterrows():
                field_name = cde_row["Field"]
                cde_meta_by_field[field_name] = {
                    "Description": cde_row.get("Description", ""),
                    "DataType": cde_row.get("DataType", ""),
                    "Validation": cde_row.get("Validation", ""),
                }

            # Apply choices for required fields (per column)
            for field_name in required_fields:
                user_choice = required_column_choices.get(field_name)
                free_text_value = required_free_text.get(field_name, "")
                enum_choice_value = required_enum_choice.get(field_name, "")

                # Precedence: Free text > Enum dropdown > Radio choice
                override_value = None
                if free_text_value:
                    override_value = free_text_value
                elif enum_choice_value:
                    override_value = enum_choice_value

                if user_choice or override_value:
                    field_meta = cde_meta_by_field.get(field_name, {})
                    prepared_df[field_name] = apply_fill_choice(
                        prepared_df[field_name],
                        user_choice,
                        field_meta,
                        override_value=override_value,
                    )

            # Apply choices for optional fields (per column)
            for field_name in optional_fields:
                user_choice_opt = optional_column_choices.get(field_name)
                free_text_opt = optional_free_text.get(field_name, "")

                override_value_opt = None
                if free_text_opt:
                    override_value_opt = free_text_opt

                if user_choice_opt or override_value_opt:
                    field_meta = cde_meta_by_field.get(field_name, {})
                    prepared_df[field_name] = apply_fill_choice(
                        prepared_df[field_name],
                        user_choice_opt,
                        field_meta,
                        override_value=override_value_opt,
                    )

            # Ensure string dtype for downstream validation
            prepared_df = prepared_df.astype("string")

            if "prepared_tables" not in st.session_state:
                st.session_state["prepared_tables"] = {}
            st.session_state["prepared_tables"][selected_table_name] = prepared_df

    # Fetch any prepared table for this selection and, if present, show preview-after + Compare button
    prepared_tables = st.session_state.get("prepared_tables", {})
    prepared_df = prepared_tables.get(selected_table_name)

    ############
    ### Step 3: CDE validation
    ############
    compare_label = f"🔍 Compare _{selected_table_name}_ vs. CDE {cde_version}"
    if prepared_df is not None:
        if (len(required_columns_with_missing) > 0) or (len(optional_columns_with_missing) > 0):
            st.markdown(
                f'###### Preview _{selected_table_name}_ <u>after</u> filling out missing values',
                unsafe_allow_html=True
            )
            st.dataframe(prepared_df.head(10))

            #### Allow user to download the prepared CSV (i.e. after filling missing values but before CDE validation)
            prepared_csv = prepared_df.to_csv(index=False)
            st.download_button(
                label=f"Click here to download this version of **_{selected_table_name}_**. ⚠️ Note it hasn't been compared vs. CDE rules",
                data=prepared_csv,
                file_name=f"{selected_table_name}_before_cde_comparison.csv",
                mime="text/csv",
            )

        #### Pause if no files loaded for CDE validation
        st.markdown("---")
        st.markdown("## Step 3: Compare file without empty values vs. the CDE rules")

        compare_state_key = f"compare_done_{selected_table_name}"
        if compare_state_key not in st.session_state:
            st.session_state[compare_state_key] = False

        compare_clicked = st.button(compare_label, key=f"compare_{selected_table_name}")

        if compare_clicked:
            st.session_state[compare_state_key] = True

        if not st.session_state.get(compare_state_key, False):
            st.info("Review the preview above. When satisfied, click the button to compare this file vs. the CDE.")
            return

        # Override the table to be validated with the prepared DataFrame
        input_dataframes_dic[selected_table_name] = prepared_df
    else:
        st.info("After choosing how to fill missing values above, click the button to apply them and see a preview.")
        return

    ############
    #### Collect results via ReportCollector and run validation
    validation_report_dic = setup_report_data(validation_report_dic, selected_table_name, input_dataframes_dic, cde_dataframe)
    report = ReportCollector()

    selected_table, cde_rules = validation_report_dic[selected_table_name]

    # Perform the validation
    st.info(f"Validating **{selected_table_name}** ({len(selected_table)} rows × {len(selected_table.columns)} columns) vs. CDE {cde_version}")
    validated_output_df, validation_report, errors_counter, warnings_counter = validate_table(selected_table, selected_table_name, cde_rules, report)

    ############
    #### Display validation results and download buttons
    report.add_divider()

    left_col, right_col = st.columns([3, 1])
    with left_col:
        st.markdown(
            '<p class="medium-font"> Download files:</p>',
            unsafe_allow_html=True,
        )
    with right_col:
        st.markdown(
            """
            <div style="text-align: right;">
                <a href="#choose-a-file-to-continue">
                    <button>⬆️ Go back to select a file</button>
                </a>
            </div>
            """,
            unsafe_allow_html=True,
        )

    def cach_clean():
        time.sleep(1)
        st.cache_data.clear()
        st.cache_resource.clear()

    report_content = report.get_log()
    table_content = validated_output_df.to_csv(index=False)

    # Download button for the markdown QC log (always enabled)
    st.download_button(
        label=f"Download a **{selected_table_name}.md** QC log markdown file",
        data=report_content,
        file_name=f"{selected_table_name}.md",
        mime="text/markdown",
        on_click=cach_clean,
    )

    # Download button (or disabled mock) for sanitized CSV depending on errors
    label_for_sanitized = f"Download a **{selected_table_name}_after_cde_comparison.csv** file"
    label_for_sanitized_html = label_for_sanitized.replace("**", "<strong>", 1).replace("**", "</strong>", 1)

    # errors_counter = 0  # For testing, uncomment this line to simulate no errors
    if errors_counter == 0:
        st.download_button(
            label=label_for_sanitized,
            data=table_content,
            file_name=f"{selected_table_name}_after_cde_comparison.csv",
            mime="text/csv",
        )
    else:
        st.markdown("""
                    <style>.disabled-btn {pointer-events: none; opacity: 0.5;}</style>
                    """, unsafe_allow_html=True)

        st.markdown(f"""
                    <button class="disabled-btn">{label_for_sanitized_html}<br><span style="font-size: 0.8em;">(File unavailable. Errors must be fixed to download this file)</span>
                    """, unsafe_allow_html=True,)
        
if __name__ == "__main__":

    main()
