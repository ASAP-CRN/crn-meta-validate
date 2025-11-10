"""
ASAP CRN metadata quality control (QC) app

GitHub repository:
https://github.com/ASAP-CRN/crn-meta-validate

Web app production version: https://asap-meta-qc.streamlit.app/
Web app staging version: https://asap-crn-crn-meta-validate-app-update-streamlit-newmodal-m1gdf4.streamlit.app/

v0.2 (CDE version v2), 20 August 2023
v0.3 (CDE version v3), 01 April 2025
v0.4 (CDE version v3.3), 07 November 2025

Authors:
- [Andy Henrie](https://github.com/ergonyc)
- [Javier Diaz](https://github.com/jdime)

Contributors:
- [Alejandro Marinez](https://github.com/AMCalejandro)

"""

################################
#### Configuration
################################

# Google Spreadsheet ID for ASAP CDE
# GOOGLE_SHEET_ID = "1xjxLftAyD0B8mPuOKUp5cKMKjkcsrp_zr9yuVULBLG8" ## CDE v1, v2 and v2.1
GOOGLE_SHEET_ID = "1c0z5KvRELdT2AtQAH2Dus8kwAyyLrR0CROhKOjpU4Vc" ## CDE v3 series
CDE_GOOGLE_SHEET_URL = f"https://docs.google.com/spreadsheets/d/{GOOGLE_SHEET_ID}/edit?usp=sharing"

use_local = False  # Set to True to read CDE from local resource folder

app_version = "ASAP CRN metadata QC app v0.4"
report_bug_email = ("mailto:javier.diazmejia@dnastack.com")
get_help_url = "https://github.com/ASAP-CRN/crn-meta-validate"
page_header = "ASAP CRN metadata quality control (QC) app"

################################
#### Imports
################################

import pandas as pd
import streamlit as st
from pathlib import Path
from utils.validate import validate_table, ReportCollector, load_css, NULL

################################
#### Expected Table Schemas and CDE Versions
################################

## Mouse scRNAseq and Spatial
MOUSE_TABLES = [
    "STUDY",
    "PROTOCOL",
    "SAMPLE",
    "MOUSE",
    "CONDITION",
    "DATA",
]

### There is HUMAN and PMDBS in the bucket names (cross compare)
### Follow Matt's nomenclature

## Human scRNAseq and Spatial
HUMAN_TABLES = [
    "STUDY",
    "PROTOCOL",
    "SUBJECT",
    "SAMPLE",
    "DATA",
    "HUMAN",
    "CLINPATH",
    "CONDITION",
]

## Cell line scRNAseq
CELL_TABLES = [
    "STUDY",
    "PROTOCOL",
    "SAMPLE",
    "CELL",
    "CONDITION",
    "DATA",
]

IPSC_TABLES = CELL_TABLES.copy()

## First element is default in the dropdown menu
SUPPORTED_METADATA_VERSIONS = [
    "v3.3",
    "v3.2",
    "v3.2-beta",
    "v3.1",
    "v3",
    "v3.0",
    "v3.0-beta",
    "v2.1",
    "v2",
    "v1",
]

################################
#### App Setup
################################

st.set_page_config(
    page_title=f"{page_header}",
    page_icon="✅",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "Get help": get_help_url,
        "Report a bug": report_bug_email,
        "About": f"#{page_header}",
    },
)

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
#### Load CDE
################################

@st.cache_data
def read_CDE(
    cde_version: str = SUPPORTED_METADATA_VERSIONS[0],
    local: bool = False,
):
    """
    Load CDE and cache it, return a dataframe and dictionary of dtypes
    """
    # Construct the path to CSD.csv
    column_list = [
        "Table",
        "Field",
        "Description",
        "DataType",
        "Required",
        "Validation",
    ]

    include_asap_ids = False
    include_aliases = False

    # set up fallback
    if cde_version == "v1":
        cd_version_file_name = "ASAP_CDE_v1"
    elif cde_version == "v2":
        cd_version_file_name = "ASAP_CDE_v2"
    elif cde_version == "v2.1":
        cd_version_file_name = "ASAP_CDE_v2.1"
    elif cde_version == "v3.0-beta":
        cd_version_file_name = "ASAP_CDE_v3.0-beta"
    elif cde_version in ["v3", "v3.0", "v3.0.0"]:
        cd_version_file_name = "ASAP_CDE_v3.0"
    elif cde_version in ["v3.1"]:
        cd_version_file_name = "ASAP_CDE_v3.1"
    elif cde_version in ["v3.2", "v3.2-beta"]:
        cd_version_file_name = "ASAP_CDE_v3.2"
    elif cde_version == "v3.3":
        cd_version_file_name = "ASAP_CDE_v3.3"
    else:
        st.error(f"ERROR!!! Unsupported cde_version: {cde_version}")
        st.stop()

    # add the Shared_key column (only for CDE v3)
    if cde_version in [
        "v3.3",
        "v3.2",
        "v3.2-beta",
        "v3.1",
        "v3",
        "v3.0",
        "v3.0-beta",
    ]:
        column_list.append("Shared_key")

    # insert "DisplayName" after "Field"
    if cde_version in ["v3.2", "v3.2-beta", "v3.3"]:
        column_list.insert(2, "DisplayName")

    # ensure we are using a supported CDE version
    if cde_version not in SUPPORTED_METADATA_VERSIONS:
        st.error(f"ERROR!!! Unsupported cde_version: {cde_version}")
        st.stop()

    # read from CDE from either local file or Google doc
    if local == True:
        root = Path(__file__).parent
        cde_local = root / f"resource/{cd_version_file_name}.csv"
        st.info(f"Using CDE {cde_version} from local resource/")
        try:
            cde_dataframe = pd.read_csv(cde_local)
        except:
            st.error(f"ERROR!!! Could not read CDE from local resource/{cde_local}")
            st.stop()
    else:
        cde_url = f"https://docs.google.com/spreadsheets/d/{GOOGLE_SHEET_ID}/gviz/tq?tqx=out:csv&sheet={cde_version}"
        st.info(f"Using CDE {cde_version} from Google doc")
        try:
            cde_dataframe = pd.read_csv(cde_url)
        except:
            st.error(f"ERROR!!! Could not read CDE from Google doc")
            st.stop()

    # drop ASAP_ids if not requested
    if not include_asap_ids:
        cde_dataframe = cde_dataframe[cde_dataframe["Required"] != "Assigned"]
        cde_dataframe = cde_dataframe.reset_index(drop=True)

    # drop Alias if not requested
    if not include_aliases:
        cde_dataframe = cde_dataframe[cde_dataframe["Required"] != "Alias"]
        cde_dataframe = cde_dataframe.reset_index(drop=True)

    # drop rows with no table name (i.e. ASAP_ids)
    cde_dataframe = cde_dataframe.loc[:, column_list]
    cde_dataframe = cde_dataframe.dropna(subset=["Table"])
    cde_dataframe = cde_dataframe.reset_index(drop=True)
    cde_dataframe = cde_dataframe.drop_duplicates()

    # force Shared_key to be int
    if cde_version in [
        "v3.3",
        "v3.2",
        "v3.2-beta",
        "v3.1",
        "v3",
        "v3.0",
        "v3.0-beta",
    ]:
        cde_dataframe["Shared_key"] = cde_dataframe["Shared_key"].fillna(0).astype(int)
    return cde_dataframe

################################
#### Run a table and return results
################################

@st.cache_data
def setup_report_data(
    report_data_dict: dict, selected_table: str, input_dataframes_dict: dict, cde_dataframe: pd.DataFrame
):
    # TODO: implement in a way to select all "ASSAY*" tables
    submit_table_df = input_dataframes_dict[selected_table]
    table_specific_cde = cde_dataframe[cde_dataframe["Table"] == selected_table]
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
        the ASAP CRN controlled vocabularies [(Common Data Elements)]({CDE_GOOGLE_SHEET_URL}).
        """,
        unsafe_allow_html=True,
    )

    ############
    #### Set dropdown menus for run settings
    col1, col2, col3 = st.columns(3)

    # Drop down menu to select dataset source
    # Currently, it includes both species and tissue/cell source. Will separate later.
    with col1:
        st.markdown('<h3 style="font-size: 20px;">1. Choose dataset source <span style="color: red;">*</span></h3>',
            unsafe_allow_html=True)
        dataset_source = st.selectbox(
            "",
            ["HUMAN", "MOUSE", "CELL", "IPSC"],
            label_visibility="collapsed",
            index=None,
            # placeholder="Select dataset source",
        )

    # Drop down menu to select dataset type (i.e. modality)
    with col2:
        st.markdown('<h3 style="font-size: 20px;">2. Choose modality <span style="color: red;">*</span></h3>',
                    unsafe_allow_html=True)
        dataset_type = st.selectbox(
            "",
            ["scRNA-seq", "Bulk RNAseq", "PROTEOMICS", "ATAC", "SPATIAL"],
            label_visibility="collapsed",
            index=None,
            # placeholder="Select TABLE..",
        )

    # Drop down menu to select CDE
    with col3:
        st.markdown('<h3 style="font-size: 20px;">3. Change metadata schema version</h3>',
                    unsafe_allow_html=True)
        cde_version = st.selectbox(
            "",
            SUPPORTED_METADATA_VERSIONS,
            label_visibility="collapsed",
        )

    ############
    #### Determine expected tables based on run settings
    table_list = []
    dataset_source_success = False
    modality_success = False

    if dataset_source == "HUMAN":
        table_list = HUMAN_TABLES
        dataset_source_success = True
    elif dataset_source == "MOUSE":
        table_list = MOUSE_TABLES
        dataset_source_success = True  
    elif dataset_source == "CELL":
        table_list = CELL_TABLES
        dataset_source_success = True
    elif dataset_source == "IPSC":
        table_list = IPSC_TABLES
        dataset_source_success = True
    else:
        dataset_source_success = False

    modality_success = False
    if dataset_type in ["scRNA-seq"]:
        table_list.append("ASSAY_RNAseq")
        modality_success = True
    elif dataset_type in ["Bulk RNAseq"]:
        table_list.append("ASSAY_RNAseq")
        modality_success = True
    elif dataset_type in ["ATAC"]:
        table_list.append("ASSAY_RNAseq")
        modality_success = True
    elif dataset_type in ["SPATIAL"]:
        table_list.append("SPATIAL")
        modality_success = True
    elif dataset_type == "PROTEOMICS":
        table_list.append("PROTEOMICS")
        modality_success = True
    else:
        modality_success = False

    ############
    #### Print expected tables and load data files

    # Request user to select dataset source and type if not done
    if not dataset_source_success or not modality_success:
        # Make pause until user selects dataset_source_success and modality_success
        st.stop()

    # Print the table list
    if len(table_list) > 0:
        table_list_formatted = ", ".join([f"{t}.csv" for t in table_list])
    else:
        st.error("No expected tables found for the selected dataset source and type")
        st.stop()

    ############
    #### Load CDE
    cde_dataframe = read_CDE(cde_version, local=use_local)

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
    st.sidebar.caption(app_version)


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
