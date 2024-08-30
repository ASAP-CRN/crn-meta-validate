"""
ASAP scRNAseq metadata data QC


https://github.com/asap_sc_collect

v0.2

metadata version v2
20 August 2023

Author:
    @ergonyc : https://github.com/ergonyc

Contributors:
    @AMCalejandro : https://github.com/AMCalejandro

"""
# conda create -n sl11 python=3.11 pip streamlit pandas

import pandas as pd
import streamlit as st

from pathlib import Path

from utils.validate import validate_table, ReportCollector, load_css, NULL

# google id for ASAP_CDE sheet
# GOOGLE_SHEET_ID = "1xjxLftAyD0B8mPuOKUp5cKMKjkcsrp_zr9yuVULBLG8"
GOOGLE_SHEET_ID = "1c0z5KvRELdT2AtQAH2Dus8kwAyyLrR0CROhKOjpU4Vc"
# Initial page config


st.set_page_config(
    page_title='ASAP CRN metadata data QC',
    page_icon="✅",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get help': "https://github.com/ergonyc/asap_sc_collect",
        'Report a bug': "mailto:henrie@datatecnica.com",
        'About': "# This is a header. This is an *extremely* cool app!"
    }
)

load_css("css/css.css")

# # Define some custom functions
# def read_file(data_file,dtypes_dict):
#     """
#     read csv or xlsx file and return a dataframe
#     """
#     if data_file.type == "text/csv":
#         df = pd.read_csv(data_file,dtype=dtypes_dict)        
#         # df = read_meta_table(table_path,dtypes_dict)
#     # assume that the xlsx file remembers the dtypes
#     elif data_file.type == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet":
#         df = pd.read_excel(data_file, sheet_name=0)
#     return df
# Function to read a table with the specified data types


# TODO: set up dataclasses to hold the data
def read_file(data_file):
    """
    TODO: depricate dtypes
    """
    encoding = 'latin1'

    if data_file.type == "text/csv":
        print(f"reading {data_file.name} txt/csv, encoding={encoding}")
        df = pd.read_csv(data_file, dtype="str", encoding=encoding)        
        # df = read_meta_table(table_path,dtypes_dict)
    # assume that the xlsx file remembers the dtypes
    elif data_file.type == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet":
        df = pd.read_excel(data_file, sheet_name=0)

    for col in df.select_dtypes(include='object').columns:
        df[col] = df[col].str.encode('latin1', errors='replace').str.decode('utf-8', errors='replace')

    df.replace({"":NULL, pd.NA:NULL}, inplace=True)

    return df

# def read_file(data_file):
#     try:
#         df = _read_file(data_file)
#     except UnicodeDecodeError:
#         df = _read_file(data_file, encoding='latin1')
#         print(f"read 'latin1' file")
#     return df
    
@st.cache_data
def load_data(data_files):
    """
    Load data from a files and cache it, return a dictionary of dataframe
    """

    tables = [dat_f.name.split('.')[0] for dat_f in data_files]
    print(tables)
    dfs = { dat_f.name.split('.')[0]:read_file(dat_f) for dat_f in data_files }

    return tables,dfs

@st.cache_data
def setup_report_data(report_dat:dict,table_choice:str, dfs:dict, CDE_df:pd.DataFrame):
    # TODO:  hack in a way to select all "ASSAY*" tables

    df = dfs[table_choice]

    hack = False
    # hack to match all ASSAY tables
    if table_choice.startswith("ASSAY"):
        hack = True

    # specific_cde_df = CDE_df[CDE_df['Table'] == table_choice]
    specific_cde_df = CDE_df[CDE_df['Table'].str.startswith(table_choice)]


    if hack:
        specific_cde_df = specific_cde_df[specific_cde_df['Table'].str.startswith("ASSAY")]
    else:
        specific_cde_df = specific_cde_df[specific_cde_df['Table'] == table_choice]

    #TODO: make sure that the loaded table is in the CDE
    dat = (df,specific_cde_df)

    report_dat[table_choice] = dat
    return report_dat


# can't cache read_ASAP_CDE so copied code here
@st.cache_data
def read_CDE(metadata_version:str="v3.0-beta", local=False):
    """
    Load CDE from local csv and cache it, return a dataframe and dictionary of dtypes
    """
    # Construct the path to CSD.csv

    if metadata_version == "v1":
        sheet_name = "ASAP_CDE_v1"
    elif metadata_version == "v2":
        sheet_name = "ASAP_CDE_v2"
    elif metadata_version == "v2.1":
        sheet_name = "ASAP_CDE_v2.1"
    elif metadata_version in ["v3.0","v3.0-beta"]:
        sheet_name = "ASAP_CDE_v3.0-beta"
    else:
        sheet_name = "ASAP_CDE_v2.1"


    if metadata_version in ["v1","v2","v2.1","v3.0-beta"]:
        print(f"metadata_version: {sheet_name}")
    else:
        print(f"Unsupported metadata_version: {sheet_name}")
        return 0,0
    
    cde_url = f"https://docs.google.com/spreadsheets/d/{GOOGLE_SHEET_ID}/gviz/tq?tqx=out:csv&sheet={sheet_name}"
    if local:
        cde_url = f"{sheet_name}.csv"
    
    try:
        CDE_df = pd.read_csv(cde_url)
        read_source = "url" if not local else "local file"
        print(f"read {read_source}")
    except:
        CDE_df = pd.read_csv(f"{sheet_name}.csv")
        print("read local file")

    # drop rows with no table name (i.e. ASAP_ids)
    CDE_df.dropna(subset=['Table'], inplace=True)

    return CDE_df

# @st.cache_data
# def convert_df(df):
#    return df.to_csv(index=False).encode('utf-8')


def main():

    # Provide template
    st.markdown('<p class="big-font">ASAP scRNAseq </p>', unsafe_allow_html=True)
    st.title('metadata data QC')
    st.markdown("""<p class="medium-font"> This app is intended to make sure ASAP Cloud 
                Platform contributions follow the ASAP CRN CDE conventions. </p> 
                <p> v0.2, updated 07Nov2023. </p> 
                """, unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        metadata_version = st.selectbox( 
                                "choose meta version👇",
                                ["v3.0-beta","v2.1","v2","v1"],
                                # index=None,
                                # placeholder="Select TABLE..",
                            )
    with col2:
        st.markdown(f'[ASAP CDE](https://docs.google.com/spreadsheets/d/{GOOGLE_SHEET_ID}/edit?usp=sharing)')

    # Load CDE from local csv
    CDE_df = read_CDE(metadata_version, local=True)


    # Once we have the dependencies, add a selector for the app mode on the sidebar.
    st.sidebar.title("Upload")
    # st.write(dtypes_dict)
    # st.write(CDE_df)
    data_files = st.sidebar.file_uploader("\tMETADATA tables:", type=['xlsx', 'csv'],accept_multiple_files=True)


    if data_files is None or len(data_files)==0: 
        st.sidebar.error("Please load data first.")
        st.stop()
        tables_loaded = False
    elif len(data_files)>0:
        tables, dfs = load_data(data_files)
        tables_loaded = True
        report_dat = dict()
    else: # should be impossible
        st.error('Something went wrong with the file upload. Please try again.')
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
    df,CDE = report_dat[table_choice]

    st.success(f"Validating n={df.shape[0]} rows from {table_choice}")
    # perform the valadation
    retval = validate_table(df, table_choice, CDE, report)

    if retval == 0:
        report.add_error(f"{table_choice} table has discrepancies!! 👎 Please try again.")


    report.add_divider()


    retval = 1
    if retval == 1:
        # st.markdown('<p class="medium-font"> You have <it>confirmed</it> your meta-data package meets all the ASAP CRN requirements. </p>', unsafe_allow_html=True )
        #from streamlit.scriptrunner import RerunException
        def cach_clean():
            time.sleep(1)
            st.runtime.legacy_caching.clear_cache()

        report_content = report.get_log()
        table_content = df.to_csv(index=False)
        #from streamlit.scriptrunner import RerunException
        def cach_clean():
            time.sleep(1)
            st.runtime.legacy_caching.clear_cache()

        # Download button
        st.download_button('📥 Download your QC log', data=report_content, file_name=f"{table_choice}.md", mime='text/markdown')

        # Download button
        st.download_button('📥 Download your QC log', data=table_content, file_name=f"{table_choice}_sanitized.csv", mime='text/csv')


        return None


if __name__ == "__main__":

    main()


    # # sex for qc
    # st.subheader('Create "biological_sex_for_qc"')
    # st.text('Count per sex group')
    # st.write(data.sex.value_counts())

    # sexes=data.sex.dropna().unique()
    # n_sexes = st.columns(len(sexes))
    # mapdic={}
    # for i, x in enumerate(n_sexes):
    #     with x:
    #         sex = sexes[i]
    #         mapdic[sex]=x.selectbox(f"[{sex}]: For QC, please pick a word below",sexes,key=i)
    #                             # ["Male", "Female","Intersex","Unnown"], key=i)
    # data['sex_qc'] = data.sex.replace(mapdic)

    # # cross-tabulation
    # st.text('=== sex_qc x sex ===')
    # xtab = data.pivot_table(index='sex_qc', columns='sex', margins=True,
    #                         values='subject_id', aggfunc='count', fill_value=0)
    # st.write(xtab)

    # sex_conf = st.checkbox('Confirm sex_qc?')
    # if sex_conf:
    #     st.info('Thank you')