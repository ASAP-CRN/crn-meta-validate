#!python3

import pandas as pd


import pandas as pd
import streamlit as st

from pathlib import Path



team = "Scherzer"
HOME = Path.home()
base_path = HOME / f"Projects/ASAP/asap-cloud-data-processing-resources/asap-ids/teams/"
test_path = base_path / f"{team.lower()}/input"

NULL = "NA"

def validate_table(schema:pd.DataFrame, df:pd.DataFrame) -> pd.DataFrame:
    # first check "Required" fields
    pass


# can't cache read_ASAP_CDE so copied code here
@st.cache_data
def read_CDE(metadata_version:str="v2.1"):
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


    CDE_df = pd.read_csv(f"{sheet_name}.csv")
    print("read local file")

    return CDE_df


def validate_table(table_in: pd.DataFrame, CDE: pd.DataFrame):
    """
    Validate a table against the CDE, and log results to streamlit (outp="streamlit") or to a 
    log file (outp="logging" or both (outp="both"|"all")
    """

    retval = 1
    table_name = specific_cde_df['Table'][0]
    # Filter out rows specific to the given table_name from the CDE
    specific_cde_df = CDE[CDE['Table'] == table_name]

    # prep table
    # convert everything to strings, and replace nan/"" with NULL
    
    table.replace

    #### REQUIRED VS OPTIONAL
    # Extract fields that are marked as "Required"
    required_fields = specific_cde_df[specific_cde_df['Required'] == "Required"]['Field'].tolist()
    optional_fields = specific_cde_df[specific_cde_df['Required'] == "Optional"]['Field'].tolist()

    # Extract fields that have a data type of "Enum" and retrieve their validation entries
    enum_fields_dict = dict(zip(specific_cde_df[specific_cde_df['DataType'] == "Enum"]['Field'], 
                               specific_cde_df[specific_cde_df['DataType'] == "Enum"]['Validation']))
    
    # This is redundant... should already be converted... but DOES capitalize first letter.   
    # table returns a copy of the table with the specified columns converted to string data type
    # table = force_enum_string(table_in, table_name, CDE)

    # Check for missing "Required" fields
    missing_required_fields = [field for field in required_fields if field not in table.columns]
    
    if missing_required_fields:
        out.add_error(f"Missing Required Fields in {table_name}: {', '.join(missing_required_fields)}")
    else:
        out.add_markdown(f"All required fields are present in *{table_name}* table.")

    # Check for empty or NaN values
    empty_fields = []
    total_rows = table.shape[0]
    for test_field,test_name in zip([required_fields, optional_fields], ["Required", "Optional"]):
        empty_or_nan_fields = {}
        for field in test_field:
            if field in table.columns:
                invalid_count = table[field].isna().sum()
                if invalid_count > 0:
                    empty_or_nan_fields[field] = invalid_count
                    
        if empty_or_nan_fields:
            out.add_error(f"{test_name} Fields with Empty (nan) values:")
            for field, count in empty_or_nan_fields.items():
                out.add_markdown(f"\n\t- {field}: {count}/{total_rows} empty rows")
            retval = 0
        else:
            out.add_markdown(f"No empty entries (Nan) found in _{test_name}_ fields.")


    # Check for invalid Enum field values
    invalid_field_values = {}
    valid_field_values = {}

    invalid_fields = []
    invalid_nan_fields = []
    for field, validation_str in enum_fields_dict.items():
        valid_values = eval(validation_str)
        if field in table.columns:
            invalid_values = table[~table[field].isin(valid_values)][field].unique()
            if invalid_values.any():

                if 'Nan' in invalid_values:
                    invalid_nan_fields.append(field)
        
                invalids = [x for x in invalid_values if x != 'Nan' ]
                if len(invalids)>0:
                    invalid_fields.append(field)    
                    invalid_field_values[field] = invalids
                    valid_field_values[field] = valid_values


    if invalid_field_values:
        out.add_subheader("Enums")
        out.add_error("Invalid entries")
        # tmp = {key:value for key,value in invalid_field_values.items() if key not in invalid_nan_fields}
        # st.write(tmp)
        def my_str(x):
            return f"'{str(x)}'"
            
        for field, values in invalid_field_values.items():
            if field in invalid_fields:
                str_out = f"- _*{field}*_:  invalid values 💩{', '.join(map(my_str, values))}\n"
                str_out += f"    - valid ➡️ {', '.join(map(my_str, valid_field_values[field]))}"
                out.add_markdown(str_out)
                # out.add_markdown( f"- {field}: invalid values {', '.join(map(str, values))}" )
                # out.add_markdown( f"- change to: {', '.join(map(my_str, valid_field_values[field]))}" )

        if len(invalid_nan_fields) > 0:
            out.add_error("Found unexpected NULL (<NA> or NaN):")
            out.add_markdown(columnize(invalid_nan_fields))
        
        retval = 0

    else:
        out.add_subheader(f"Enum fields have valid values in {table_name}. 🥳")

    return retval


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
                                ["v2.1","v2","v1"],
                                # index=None,
                                # placeholder="Select TABLE..",
                            )
    with col2:
        st.markdown('[ASAP CDE](https://docs.google.com/spreadsheets/d/1xjxLftAyD0B8mPuOKUp5cKMKjkcsrp_zr9yuVULBLG8/edit?usp=sharing)')

    #     fields = specific_cde_df["Field"].unique()
    
    for field in fields:

if __name__ == "__main__":

    main()
