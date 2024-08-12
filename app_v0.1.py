# imports
import streamlit as st
import pandas as pd
from utils.qcutils import validate_table
from utils.io import ReportCollector, read_file, load_css
import time



LOG_NAME = "report.md"


load_css("css/css.css")
# Provide template
st.markdown('<p class="big-font"> ASAP single cell data self-QC app</p>', unsafe_allow_html=True)
st.markdown('<p class="medium-font"> This app is intended to make sure ASAP contributing with single cell data provide standard ASAP required fields </p>', unsafe_allow_html=True)
st.markdown('[Access the data dictionary and template](https://docs.google.com/spreadsheets/d/1xjxLftAyD0B8mPuOKUp5cKMKjkcsrp_zr9yuVULBLG8/edit?usp=sharing)', unsafe_allow_html=True)



# Read file from streamlit and create a copy to do the maps
data_file = st.sidebar.file_uploader("Upload Your meta-tables (SAMPLE.csv, STUDY.csv, PROTOCOL.csv, CLINPATH.csv, and/or SUBJECT.csv)", type=['xlsx', 'csv'],accept_multiple_files=True)
# datamaps_copy = [dat.copy() for dat in data]


# Construct the path to CSD.csv
cde_file_path = "ASAP_CDE.csv"
CDE_df = pd.read_csv(cde_file_path)


if data_file is None or len(data_file)==0: 
    st.stop()
elif len(data_file)>0:
    tables = [dat_f.name.split('.')[0] for dat_f in data_file]
    data = [ read_file(dat_f) for dat_f in data_file]
else: # should be impossible
    st.error('Something went wrong with the file upload. Please try again.')
    st.stop()


out = ReportCollector()


confirm_table = {}
for table_name,dat in zip(tables,data):

    out.add_header(f"{table_name} table ({table_name}.csv)")
    # data_file = "https://docs.google.com/spreadsheets/d/1xjxLftAyD0B8mPuOKUp5cKMKjkcsrp_zr9yuVULBLG8/edit?usp=sharing"
    # Load the CDE.csv file and the reference table

    # TODO: check order of columns

    retval = validate_table(dat, table_name, CDE_df, out)

    if retval == 0:
        out.add_error(f"{table_name} table validation FAILED!! 👎 Please try again.")

    confirm_table[table_name] = st.checkbox(f'Confirm {table_name}?')
    if confirm_table[table_name]:
        st.info('Thank you')

    out.add_divider()



if st.button("Finished?"):
    #if not (clinical_conf & ph_conf & sex_conf & race_conf & fh_conf & rg_conf):
    if not all([confirm_table[tab] for tab in tables]):
        out.add_error('Did you forget to confirm any of the steps above?')
        out.add_error("Please, tick all the boxes on the previous steps if the QC to meet GP2 standard format was successful")
    else:
        # Generate log for download
        st.markdown('<p class="medium-font"> You have _confirmed_ your meta-data package meets all the ASAP CRN requirements. </p>', unsafe_allow_html=True )
        
        report_content = out.get_log()

        #from streamlit.scriptrunner import RerunException
        def cach_clean():
            time.sleep(1)
            st.runtime.legacy_caching.clear_cache()

        # Download button
        st.download_button('📥 Download your QC log', data=report_content, file_name=LOG_NAME, mime='text/markdown')









# Check all columns are present in the input 
# We can do something such as checking the number of columns matches what we would expect ( a bit unsafe tho)
# Otherwise, create a list with all col names



# # Check all required columns are not missing
# required_cols = [col for col in data.columns if col not in optional_cols]

# data_non_miss_check = data[required_cols].copy()

# if data_non_miss_check.isna().sum().sum()>0:
#     st.error('There are some missing entries in the required columns. Please fill the missing cells ')
#     st.text('First 30 entries with missing data in any required fields')
#     st.write(data_non_miss_check[data_non_miss_check.isna().sum(1)>0].head(30))
#     st.stop()
# else:
#     st.text('Check missing data in the required fields --> OK')



# Perform numeric variables specific checks (ie, are thay on a sensible range or we can detect errors?)



# # Example on how to map users code to our standard codes
# # If we use this approach I would like to avoid code repetition and try to wrap this on a function and a for loop 
# # I do not want to have this same thing 100 times
# # Also, let's think if we can come up with something cooler to do this, something that looks nicer

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
#         mapdic[sex]=x.selectbox(f"[{sex}]: For QC, please pick a word below",
#                             ["Male", "Female","Intersex","Unnown"], key=i)
# data['sex_qc'] = data.sex.replace(mapdic)

# # cross-tabulation
# st.text('=== sex_qc x sex ===')
# xtab = data.pivot_table(index='sex_qc', columns='sex', margins=True,
#                         values='sample_id', aggfunc='count', fill_value=0)
# st.write(xtab)

# sex_conf = st.checkbox('Confirm sex_qc?')
# if sex_conf:
#     st.info('Thank you')


