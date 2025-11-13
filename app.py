"""
ASAP CRN metadata quality control (QC) app

GitHub repository:
https://github.com/ASAP-CRN/crn-meta-validate

Web app production version: https://asap-meta-qc.streamlit.app/
Web app staging version: https://asap-crn-crn-meta-validate-app-update-streamlit-newmodal-m1gdf4.streamlit.app/

Webapp v0.2 (CDE version v2), 20 August 2023
Webapp v0.3 (CDE version v3), 01 April 2025
Webapp v0.4 (CDE version v3.3), 11 November 2025

Version notes:
Webapp v0.4:
* CDE version is provided in resource/app_schema_{webapp_version}.json and loaded via utils/cde.py
* Added supported species, modality and tissue/cell source dropdowns to select expected tables
* Added reset button to sidebar, reset cache and file uploader
* Added app_schema to manage app configuration
* Added Classes for DelimiterHandler and ProcessedDataLoader to utils/
* Improved delimiter detection and handling logic
* Improved file upload handling and status display

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
import streamlit as st
from pathlib import Path
import os, sys
import re
from io import StringIO
from utils.validate import validate_table, ReportCollector, NULL
from utils.cde import read_CDE, get_table_cde
from utils.delimiter_handler import DelimiterHandler
from utils.processed_data_loader import ProcessedDataLoader

webapp_version = "v0.4"

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
cde_google_sheet = f"https://docs.google.com/spreadsheets/d/{cde_spreadsheet_id}/gviz/tq?tqx=out:csv&sheet={cde_version}"
use_local = False  # Set to False to use Google Sheets

# Extract table categories
SPECIES = app_schema['table_categories']['species']
TISSUES_OR_CELLS = app_schema['table_categories']['tissues_or_cells']
MODALITIES = app_schema['table_categories']['modalities']

# Extract mandatory table names
MANDATORY_TABLES = app_schema['table_names']['mandatory']

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
        
        We do this in two steps:
        1. First, the app helps to fix common issues like filling out missing values.
        2. Second, it identifies missing columns and value mismatches vs.
        the ASAP CRN controlled vocabularies [(Common Data Elements)]({cde_google_sheet}).

        Two types of issues will be reported:
        - **Errors**: Must be fixed by the data contributors before uploading data to ASAP CRN.
        - **Warnings**: Recommended to fix before uploading, but not mandatory. Missing values will be filled out with 'NA' in sanitized files.


        """,
        unsafe_allow_html=True,
    )

    ############
    ### Load CSS (text size, colors, etc.)
    load_css(os.path.join(repo_root, "css", "css.css"))

    ############
    #### Set dropdown menus for run settings
    col1, col2, col3 = st.columns(3)

    # Drop down menu to select species
    # Currently, it includes both species and tissue/cell source. Will separate later.
    with col1:
        st.markdown('<h3 style="font-size: 20px;">1. Choose dataset species <span style="color: red;">*</span></h3>',
            unsafe_allow_html=True)
        species = st.selectbox(
            "",
            SPECIES,
            label_visibility="collapsed",
            index=None
        )

    # Drop down menu to select tissue/cell source
    with col2:
        st.markdown('<h3 style="font-size: 20px;">2. Choose tissue/cell <span style="color: red;">*</span></h3>',
                    unsafe_allow_html=True)
        tissue_or_cell = st.selectbox(
            "",
            TISSUES_OR_CELLS,
            label_visibility="collapsed",
            index=None
        )

    # Drop down menu to select modality
    with col3:
        st.markdown('<h3 style="font-size: 20px;">3. Choose modality <span style="color: red;">*</span></h3>',
                    unsafe_allow_html=True)
        modality = st.selectbox(
            "",
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

    table_list = MANDATORY_TABLES.copy()

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
    
    if st.sidebar.button("Reset App", use_container_width=True, type="primary"):
        st.cache_data.clear() # Clear all cached data
        st.session_state.file_uploader_key += 1 # Increment the file uploader key to reset it
        # Clear delimiter decisions and invalid files
        if 'delimiter_decisions' in st.session_state:
            st.session_state.delimiter_decisions = {}
        if 'invalid_files' in st.session_state:
            st.session_state.invalid_files = set()
        st.rerun()

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
                st.markdown("### Step 2: Apply your delimiter decisions")
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
                        st.caption(f"Status: {status_str}")
                    except Exception:
                        pass
            # Stop here and wait for the button to be clicked
            st.stop()

        ############
        #### Process valid files
        loader = ProcessedDataLoader()
        table_names, input_dataframes_dic, file_warnings, row_counts = loader.load(processed_files)

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

        st.markdown("---")

        ############
        #### Left-side menu logic for uploaded files
        # Log files for CDE validation
        if len(valid_files) > 0:
            st.sidebar.markdown("**Valid files:**")

        for data_file in valid_files:
            file_key = delimiter_handler.get_file_key(data_file.name, data_file.size)
            if file_key in st.session_state.get('delimiter_decisions', {}):
                file_content = data_file.getvalue()
                detected_delimiter, confidence, preview_df = delimiter_handler.detect_delimiter(file_content, data_file.name)
                delimiter_name = delimiter_handler.get_delimiter_name(detected_delimiter)
                
                decision = st.session_state.delimiter_decisions[file_key]
                # Decision is stored as a dict with 'action' key
                action = decision.get('action') if isinstance(decision, dict) else decision
                if action == 'convert':
                    st.sidebar.success(f"✓ {data_file.name} converted from {delimiter_name} to comma")
                else:
                    st.sidebar.info(f"✗ {data_file.name} kept with {delimiter_name} delimiter")
        
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
    #### Pause if no files loaded for CDE validation
    if not tables_loaded:
        st.stop()

    ############
    #### Create file selection dropdown and run CDE validation for each selected file
    st.markdown('<h3 style="font-size: 20px;">4. Choose file to validate</h3>',
                unsafe_allow_html=True)
    selected_table_name = st.selectbox(
        "",
        table_names,
        label_visibility="collapsed",
    )

    ############
    #### Collect results via ReportCollector
    validation_report_dic = setup_report_data(validation_report_dic, selected_table_name, input_dataframes_dic, cde_dataframe)
    report = ReportCollector()

    ############
    #### Unpack data
    selected_table, cde_rules = validation_report_dic[selected_table_name]

    ############
    #### Perform the validation
    # NOTE: validate_table() is where empty strings are filled out with NULL string
    st.info(f"Validating **{selected_table_name}** ({len(selected_table.index)} rows × {len(selected_table.columns)} columns) vs. CDE {cde_version}")
    # status_code = validate_table(selected_table, selected_table_name, cde_rules, report)
    validated_output_df, validation_report, errors_counter, warnings_counter = validate_table(selected_table, selected_table_name, cde_rules, report)

    ############
    #### Display validation results and download buttons

    report.add_divider()

    st.markdown(f'<p class="medium-font"> Download files:</p>',
    unsafe_allow_html=True )
    def cach_clean():
        time.sleep(1)
        st.runtime.legacy_caching.clear_cache()

    report_content = report.get_log()
    table_content = validated_output_df.to_csv(index=False)

    # Download button
    st.download_button(
        label=f"📥 Download a **{selected_table_name}.md** QC log markdown file",
        data=report_content,
        file_name=f"{selected_table_name}.md",
        mime="text/markdown",
    )

    # errors_counter = 1 # For testing purposes, set to 0 to always allow download

    label_for_sanitized = f"📥 Download a **{selected_table_name}_sanitized.csv** file"
    label_for_sanitized_html = label_for_sanitized.replace("**", "<strong>", 1).replace("**", "</strong>", 1)
    if errors_counter == 0:
        st.download_button(
            label=label_for_sanitized,   # Markdown works here
            data=table_content,
            file_name=f"{selected_table_name}_sanitized.csv",
            mime="text/csv",
        )
    else:
        st.markdown("""
                    <style>.disabled-btn {pointer-events: none; opacity: 0.5;}</style>
                    """, unsafe_allow_html=True)

        st.markdown(f"""
                    <button class="disabled-btn">{label_for_sanitized_html}</button><span> (disabled due to errors in the table. Please fix errors before downloading sanitized file.)</span>
                    """, unsafe_allow_html=True,)

if __name__ == "__main__":

    main()
