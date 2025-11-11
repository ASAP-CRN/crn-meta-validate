"""
ASAP CRN metadata quality control (QC) app

GitHub repository:
https://github.com/ASAP-CRN/crn-meta-validate

Web app production version: https://asap-meta-qc.streamlit.app/
Web app staging version: https://asap-crn-crn-meta-validate-app-update-streamlit-newmodal-m1gdf4.streamlit.app/

Webapp v0.2 (CDE version v2), 20 August 2023
Webapp v0.3 (CDE version v3), 01 April 2025
Webapp v0.4 (CDE version v3.3), 07 November 2025

Version notes:
Webapp v0.4:
* CDE version is hardcoded in resource/app_schema_{webapp_version}.json
* Added supported species, modality and tissue/cell source dropdowns to select expected tables
* Added reset button to sidebar, reset cache and file uploader

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
from utils.validate import validate_table, ReportCollector, load_css, NULL
from utils.cde import read_CDE, get_table_cde

webapp_version = "v0.4"

################################
#### Load app schema from JSON
################################
root = Path(__file__).parent
app_schema_path = root / f"resource/app_schema_{webapp_version}.json"
with open(app_schema_path, "r") as f:
    app_schema = json.load(f)

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

## Load CSS (text size, colors, etc.)
load_css("css/css.css")

# TODO: set up dataclasses to hold the data
def read_csv(data_file):
    """
    TODO: implement other infile formats
    """

    def sanitize_validation_string(validation_str):
        """Sanitize validation strings by replacing smart quotes with straight quotes."""
        if not isinstance(validation_str, str):
            return validation_str
        return (
            validation_str.replace('"', '"')
            .replace('"', '"')
            .replace(""", "'").replace(""", "'")
            .replace("…", "...")
        )

    encoding = "latin1"

    if data_file.type == "text/csv":
        print(f"reading {data_file.name} csv, encoding={encoding}")
        table_df = pd.read_csv(data_file, dtype="str", encoding=encoding)
    else:
        st.error(f"Unsupported file type: {data_file.type}")
        st.stop() 

    for col in table_df.select_dtypes(include="object").columns:
        table_df[col] = (
            table_df[col]
            .str.encode("latin1", errors="replace")
            .str.decode("utf-8", errors="replace")
        )
    for col in table_df.columns:
        table_df[col] = table_df[col].apply(sanitize_validation_string)

    # drop the first column if it is just the index incase it was saved with index = True
    if table_df.columns[0] == "Unnamed: 0":
        table_df = table_df.drop(columns=["Unnamed: 0"])
        print("dropped Unnamed: 0")

    # drop rows with all null values
    table_df.dropna(how="all", inplace=True)
    table_df.fillna(NULL, inplace=True)
    table_df.replace(
        {"": NULL, pd.NA: NULL, "none": NULL, "nan": NULL, "Nan": NULL}, inplace=True
    )
    return table_df.reset_index(drop=True)


################################
#### Load input tables
################################

@st.cache_data
def load_data(data_files):
    """
    Load data from files and cache it, return a list of table names and a dictionary of dataframes
    """
    table_names = [data_file.name.split(".")[0] for data_file in data_files]
    input_dataframes_dict = {data_file.name.split(".")[0]: read_csv(data_file) for data_file in data_files}
    return table_names, input_dataframes_dict

################################
#### Run a table and return results
################################

@st.cache_data
def setup_report_data(
    report_data_dict: dict, selected_table: str, input_dataframes_dict: dict, cde_dataframe: pd.DataFrame
):
    # TODO: implement in a way to select all "ASSAY*" tables
    submit_table_df = input_dataframes_dict[selected_table]
    table_specific_cde = get_table_cde(cde_dataframe, selected_table)
    # TODO: make sure that the loaded table is in the CDE
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
    st.markdown('<p class="big-font">ASAP CRN metadata quality control (QC) app</p>', unsafe_allow_html=True)
    st.markdown(
        f"""
        This app assists ASAP CRN data contributors to QC their metadata tables (e.g. STUDY.csv, SAMPLE.csv, 
        PROTOCOL.csv, etc.) before uploading them to ASAP CRN Google buckets.
        
        * Helps to fix common issues like filling out missing values.
        * Suggests corrections like identifying missing columns and value mismatches vs. 
        the ASAP CRN controlled vocabularies [(Common Data Elements)]({cde_google_sheet}).
        """,
        unsafe_allow_html=True,
    )

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
        species_specific_table_key = f"{species.lower()}_specific"
        table_list.extend(app_schema['table_names'][species_specific_table_key])

        if tissue_or_cell in TISSUES_OR_CELLS:
            tissue_or_cell_success = True
            if tissue_or_cell in [app_schema['table_names']['cell_specific']]:
                table_list.extend(app_schema['table_names']['cell_specific'])

            if modality in MODALITIES:
                modality_success = True
                if modality in ["single cell/nucleus RNA-seq", "Bulk RNAseq", "ATAC-seq"]:
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

    if data_files is None or len(data_files) == 0:
        tables_loaded = False
    elif len(data_files) > 0:
        table_names, input_dataframes_dic = load_data(data_files)
        tables_loaded = True
        validation_report_dic = dict()
        st.sidebar.success(f"N={len(table_names)} files loaded")
    else:
        st.error("Something went wrong with the file upload. Please try again.")
        st.stop()
        tables_loaded = False

    ############
    #### Add Reset button and version info to sidebar
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
        st.rerun()

    ## Add app version
    st.sidebar.caption(version_display)


    ############
    #### Pause if no files loaded
    if not tables_loaded:
        st.stop()

    ############
    #### Create file selection dropdown and run validation
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown('<h3 style="font-size: 20px;">4. Choose file to validate</h3>',
                    unsafe_allow_html=True)
        selected_table_name = st.selectbox(
            "",
            table_names,
            label_visibility="collapsed",
        )

    # Collect results via ReportCollector
    validation_report_dic = setup_report_data(validation_report_dic, selected_table_name, input_dataframes_dic, cde_dataframe)
    report = ReportCollector()

    # Unpack data
    selected_table, cde_rules = validation_report_dic[selected_table_name]

    # Perform the validation
    st.info(f"Validating n={selected_table.shape[0]} rows from {selected_table_name}")
    status_code = validate_table(selected_table, selected_table_name, cde_rules, report)
    validated_output_df, validation_output = validation_report_dic[selected_table_name]
    if status_code == 0:
        report.add_error(
            f"{selected_table_name} table has discrepancies!! 👎 Please try again."
        )
    report.add_divider()

    ############
    #### Display validation results and download buttons

    status_code = 1 # force success for download
    if status_code == 1:
        st.markdown('<p class="medium-font"> Download logs and a sanitized .csv </p>',
        unsafe_allow_html=True )
        # from streamlit.scriptrunner import RerunException
        def cach_clean():
            time.sleep(1)
            st.runtime.legacy_caching.clear_cache()

        report_content = report.get_log()
        table_content = validated_output_df.to_csv(index=False)

        # from streamlit.scriptrunner import RerunException
        def cach_clean():
            time.sleep(1)
            st.runtime.legacy_caching.clear_cache()

        # Download button
        st.download_button(
            "📥 Download your QC log",
            data=report_content,
            file_name=f"{selected_table_name}.md",
            mime="text/markdown",
        )

        # Download button
        st.download_button(
            "📥 Download a sanitized .csv (NULL-> 'NA' )",
            data=table_content,
            file_name=f"{selected_table_name}_sanitized.csv",
            mime="text/csv",
        )
        return None

if __name__ == "__main__":

    main()
