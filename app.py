"""
ASAP scRNAseq metadata data QC app

https://github.com/ASAP-CRN/crn-meta-validate

v0.2 (CDE version v2), 20 August 2023
v0.3 (CDE version v3), 01 April 2025
v0.4 (CDE version v3), DAY November 2024

Authors:
- [Andy Henrie](https://github.com/ergonyc)
- [Javier Diaz](https://github.com/jdime)

Contributors:
- [Alejandro Marinez](https://github.com/AMCalejandro)

"""

import pandas as pd
import streamlit as st

from pathlib import Path

from utils.validate import validate_table, ReportCollector, load_css, NULL

# Google Spreadsheet ID for ASAP CDE
# GOOGLE_SHEET_ID = "1xjxLftAyD0B8mPuOKUp5cKMKjkcsrp_zr9yuVULBLG8" ## CDE v1, v2 and v2.1
GOOGLE_SHEET_ID = "1c0z5KvRELdT2AtQAH2Dus8kwAyyLrR0CROhKOjpU4Vc" ## CDE v3 series
CDE_GOOGLE_SHEET_URL = f"https://docs.google.com/spreadsheets/d/{GOOGLE_SHEET_ID}/edit?usp=sharing"

## Mouse scRNAseq and Spatial
MOUSE_TABLES = [
    "STUDY",
    "PROTOCOL",
    "SAMPLE",
    "MOUSE",
    "CONDITION",
    "DATA",
]

## Human scRNAseq and Spatial
PMDBS_TABLES = [
    "STUDY",
    "PROTOCOL",
    "SUBJECT",
    "SAMPLE",
    "DATA",
    "PMDBS",
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

st.set_page_config(
    page_title="ASAP CRN metadata data QC",
    page_icon="✅",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "Get help": "https://github.com/ASAP-CRN/crn-meta-validate",
        "Report a bug": "mailto:javier.diazmejia@dnastack.com",
        "About": "# ASAP scRNAseq metadata data QC app",
    },
)

load_css("css/css.css")

# TODO: set up dataclasses to hold the data
def read_file(data_file):
    """
    TODO: depricate dtypes
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
        print(f"reading {data_file.name} txt/csv, encoding={encoding}")
        df = pd.read_csv(data_file, dtype="str", encoding=encoding)
        # df = read_meta_table(table_path,dtypes_dict)
    # assume that the xlsx file remembers the dtypes
    elif (
        data_file.type
        == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    ):
        df = pd.read_excel(data_file, resource_fname=0)

    for col in df.select_dtypes(include="object").columns:
        df[col] = (
            df[col]
            .str.encode("latin1", errors="replace")
            .str.decode("utf-8", errors="replace")
        )
    for col in df.columns:
        df[col] = df[col].apply(sanitize_validation_string)

    # drop the first column if it is just the index incase it was saved with index = True
    if df.columns[0] == "Unnamed: 0":
        df = df.drop(columns=["Unnamed: 0"])
        print("dropped Unnamed: 0")

    # drop rows with all null values
    df.dropna(how="all", inplace=True)
    df.fillna(NULL, inplace=True)
    df.replace(
        {"": NULL, pd.NA: NULL, "none": NULL, "nan": NULL, "Nan": NULL}, inplace=True
    )

    return df.reset_index(drop=True)

@st.cache_data
def load_data(data_files):
    """
    Load data from a files and cache it, return a dictionary of dataframe
    """

    tables = [dat_f.name.split(".")[0] for dat_f in data_files]
    dfs = {dat_f.name.split(".")[0]: read_file(dat_f) for dat_f in data_files}

    return tables, dfs


@st.cache_data
def setup_report_data(
    report_dat: dict, table_choice: str, dfs: dict, CDE_df: pd.DataFrame
):
    # TODO:  hack in a way to select all "ASSAY*" tables

    df = dfs[table_choice]

    specific_cde_df = CDE_df[CDE_df["Table"] == table_choice]
    # TODO: make sure that the loaded table is in the CDE
    dat = (df, specific_cde_df)

    report_dat[table_choice] = dat

    return report_dat


@st.cache_data
def read_CDE(
    metadata_version: str = "v3.2",
    local: bool = False,
):
    """
    Load CDE from local csv and cache it, return a dataframe and dictionary of dtypes
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
    if metadata_version == "v1":
        resource_fname = "ASAP_CDE_v1"
    elif metadata_version == "v2":
        resource_fname = "ASAP_CDE_v2"
    elif metadata_version == "v2.1":
        resource_fname = "ASAP_CDE_v2.1"
    elif metadata_version == "v3.0-beta":
        resource_fname = "ASAP_CDE_v3.0-beta"
    elif metadata_version in ["v3", "v3.0", "v3.0.0"]:
        resource_fname = "ASAP_CDE_v3.0"
    elif metadata_version in ["v3.1"]:
        resource_fname = "ASAP_CDE_v3.1"
    elif metadata_version in ["v3.2", "v3.2-beta"]:
        resource_fname = "ASAP_CDE_v3.2"
    elif metadata_version == "v3.3":
        resource_fname = "ASAP_CDE_v3.3"
    else:
        resource_fname = "ASAP_CDE_v3.2"

    # add the Shared_key column for v3
    if metadata_version in [
        "v3.3",
        "v3.2",
        "v3.2-beta",
        "v3.1",
        "v3",
        "v3.0",
        "v3.0-beta",
    ]:
        column_list.append("Shared_key")
        # column_list += ["Shared_key"]

    # insert "DisplayName" after "Field"
    if metadata_version in ["v3.2", "v3.2-beta", "v3.3"]:
        column_list.insert(2, "DisplayName")

    if metadata_version in SUPPORTED_METADATA_VERSIONS:
        print(f"metadata_version: {resource_fname}")
    else:
        print(f"Unsupported metadata_version: {resource_fname}")

    cde_url = f"https://docs.google.com/spreadsheets/d/{GOOGLE_SHEET_ID}/gviz/tq?tqx=out:csv&sheet={metadata_version}"
    print(cde_url)

    if local:
        root = Path(__file__).parent
        cde_url = root / f"resource/{resource_fname}.csv"
        print(f"reading from resource/{resource_fname}.csv")
    else:
        print(f"reading from googledoc {cde_url}")

    try:
        CDE_df = pd.read_csv(cde_url)
        print(f"read CDE")
    except:
        root = Path(__file__).parent
        CDE_df = pd.read_csv(f"{root}/resource/{resource_fname}.csv")
        print(f"exception:read fallback file: ./resource/{resource_fname}.csv")

    # drop ASAP_ids if not requested
    if not include_asap_ids:
        CDE_df = CDE_df[CDE_df["Required"] != "Assigned"]
        CDE_df = CDE_df.reset_index(drop=True)
        # print(f"dropped ASAP_ids")

    # drop Alias if not requested
    if not include_aliases:
        CDE_df = CDE_df[CDE_df["Required"] != "Alias"]
        CDE_df = CDE_df.reset_index(drop=True)
        # print(f"dropped Alias")

    # drop rows with no table name (i.e. ASAP_ids)
    CDE_df = CDE_df.loc[:, column_list]
    CDE_df = CDE_df.dropna(subset=["Table"])
    CDE_df = CDE_df.reset_index(drop=True)
    CDE_df = CDE_df.drop_duplicates()

    # force Shared_key to be int
    if metadata_version in [
        "v3.3",
        "v3.2",
        "v3.2-beta",
        "v3.1",
        "v3",
        "v3.0",
        "v3.0-beta",
    ]:
        CDE_df["Shared_key"] = CDE_df["Shared_key"].fillna(0).astype(int)

    return CDE_df


def main():

    # Provide template
    st.markdown('<p class="big-font">ASAP CRN metadata quality control (QC) app</p>', unsafe_allow_html=True)
    st.markdown(
        f"""
        This app assists ASAP Team data contributors to QC their metadata tables (e.g. STUDY.csv, SAMPLE.csv, PROTOCOL.csv, etc.)
        before uploading them to ASAP CRN Cloud Google Buckets.
        
        * Helps to fix common issues like filling out missing values.
        * Suggests corrections like identifying missing columns and data value mismatches 
        based on the ASAP CRN controlled vocabularies [Common Data Elements]({CDE_GOOGLE_SHEET_URL}).
        * Version v0.4 (DAY/Nov/2025).
        """,
        unsafe_allow_html=True,
    )

    col1, col2 = st.columns(2)

    with col1:
        metadata_version = st.selectbox(
            "1) Choose metadata schema version",
            ["v3.2", "v3.3", "v3.1", "v3.0", "v3.0-beta", "v2.1", "v2", "v1"],
            # index=None,
            # placeholder="Select TABLE..",
        )
    # with col2:
        # st.markdown(
        #     f"[ASAP CDE](https://docs.google.com/spreadsheets/d/{GOOGLE_SHEET_ID}/edit?usp=sharing)"
        # )
        # st.write(f"metadata_version: {metadata_version}")

    # add a pull down to select the dataset source in first column
    with col1:
        dataset_source = st.selectbox(
            "2) Choose dataset 'source'",
            ["PMDBS", "CELL", "IPSC", "MOUSE"],
            index=None,
            placeholder="Select TABLE..",
        )
    with col2:
        # add a pull down to select dataset type in the second column
        dataset_type = st.selectbox(
            "3) Choose dataset 'type'",
            ["RNAseq", "PROTEOMICS", "ATAC"],
            index=None,
            placeholder="Select TABLE..",
        )

    # add a checkbox to indicate if we are dealing with a Spatial dataset
    with col1:
        is_spatial = st.checkbox("Is this a Spatial dataset?")
    # with col2:
    #     st.write(f"is_spatial: {is_spatial}")
    
    table_success = False

    if dataset_source == "PMDBS":
        table_list = PMDBS_TABLES
    elif dataset_source == "CELL":
        table_list = CELL_TABLES
    elif dataset_source == "IPSC":
        table_list = IPSC_TABLES
    elif dataset_source == "MOUSE":
        table_list = MOUSE_TABLES
    else:
        table_list = []

    if dataset_type in ["RNAseq", "ATAC"]:
        table_list.append("ASSAY_RNAseq")
        table_success = True
    elif dataset_type == "PROTEOMICS":
        table_list.append("PROTEOMICS")
        table_success = True
    else:
        print(f"dataset_type: {dataset_type} not supported")
        tabe_success = False

    if is_spatial:
        table_list.append("SPATIAL")
        spatial_text = " (Spatial)"
    else:
        spatial_text = ""

    # print the table list
    if len(table_list) > 0:
        st.write(
            f"Your {spatial_text} {dataset_type}  dataset's tables should be: {table_list}"
        )

    # Load CDE from local csv
    CDE_df = read_CDE(metadata_version, local=False)

    # add a call to action to load the files in the sidebar
    if not table_success:
        st.error("Please select a dataset source and type.")
        st.stop()
    # else:
    #     st.sidebar.success(f"Please load your metadata tables")
        # st.success(f"↖️ Please load your metadata tables")

    # Once we have the dependencies, add a selector for the app mode on the sidebar.
    st.sidebar.title("Upload")
    metadata_tables_text = " ".join([f"\t{t}, \n " for t in table_list])
    data_files = st.sidebar.file_uploader(
        f"Load your dataset's metadata CSV files: \n{metadata_tables_text}",
        type=["csv"],
        accept_multiple_files=True,
    )

    if data_files is None or len(data_files) == 0:
        st.sidebar.error("Please load data first.")
        st.stop()
        tables_loaded = False
    elif len(data_files) > 0:
        tables, dfs = load_data(data_files)
        tables_loaded = True
        report_dat = dict()
    else:  # should be impossible
        st.error("Something went wrong with the file upload. Please try again.")
        st.stop()
        tables_loaded = False

    if tables_loaded:
        st.sidebar.success(f"N={len(tables)} Tables loaded successfully")
        st.sidebar.info(f'loaded Tables : {", ".join(map(str, tables))}')

        col1, col2 = st.columns(2)

        with col1:
            table_choice = st.selectbox(
                "Choose the TABLE to validate 👇",
                tables,
                # index=None,
                # placeholder="Select TABLE..",
            )
        with col2:
            # st.write('You selected:', table_choice)
            st.success(f"You selected: {table_choice}")

    # once tables are loaded make a dropdown to choose which one to validate
    # initialize the data structure and instance of ReportCollector
    report_dat = setup_report_data(report_dat, table_choice, dfs, CDE_df)
    report = ReportCollector()

    # unpack data
    print(f"{report_dat.keys()=}")
    print(table_choice)

    df, CDE = report_dat[table_choice]

    st.success(f"Validating n={df.shape[0]} rows from {table_choice}")
    # perform the valadation
    retval = validate_table(df, table_choice, CDE, report)

    df_out, out = report_dat[table_choice]

    if retval == 0:
        report.add_error(
            f"{table_choice} table has discrepancies!! 👎 Please try again."
        )

    report.add_divider()

    retval = 1
    if retval == 1:
        # st.markdown('<p class="medium-font"> You have <it>confirmed</it> your meta-data package meets all the ASAP CRN requirements. </p>', 
        # unsafe_allow_html=True )
        # from streamlit.scriptrunner import RerunException
        def cach_clean():
            time.sleep(1)
            st.runtime.legacy_caching.clear_cache()

        report_content = report.get_log()
        table_content = df_out.to_csv(index=False)

        # from streamlit.scriptrunner import RerunException
        def cach_clean():
            time.sleep(1)
            st.runtime.legacy_caching.clear_cache()

        # Download button
        st.download_button(
            "📥 Download your QC log",
            data=report_content,
            file_name=f"{table_choice}.md",
            mime="text/markdown",
        )

        # Download button
        st.download_button(
            "📥 Download a sanitized .csv (NULL-> 'NA' )",
            data=table_content,
            file_name=f"{table_choice}_sanitized.csv",
            mime="text/csv",
        )

        return None


if __name__ == "__main__":

    main()
