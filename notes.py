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

from utils.qcutils import validate_table, GOOGLE_SHEET_ID
from utils.io import ReportCollector, load_css, get_dtypes_dict
from pydantic import BaseModel, ValidationError, constr, conint, confloat
from enum import Enum


# google id for ASAP_CDE sheet
GOOGLE_SHEET_ID = "1xjxLftAyD0B8mPuOKUp5cKMKjkcsrp_zr9yuVULBLG8"

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

class ColumnAEnum(str, Enum):
    value1 = "value1"
    value2 = "value2"
    value3 = "value3"

class DataRow(BaseModel):
    column_a: ColumnAEnum
    column_b: constr(strict=True, min_length=1)
    column_c: conint(strict=True, ge=0)
    column_d: confloat(strict=True, ge=0.0)

def load_csv(file_path):
    return pd.read_csv(file_path)

def validate_row(row):
    try:
        data_row = DataRow(
            column_a=row['column_a'],
            column_b=row['column_b'],
            column_c=row['column_c'],
            column_d=row['column_d']
        )
        return True, data_row
    except ValidationError as e:
        print(f"Validation error: {e}")
        return False, None

def edit_row(row):
    print("Please edit the invalid entries:")
    for col in row.index:
        new_value = input(f"Enter a valid value for {col} (current: {row[col]}): ")
        row[col] = new_value
    return row

def main():
    file_path = 'your_file.csv'
    df = load_csv(file_path)

    for index, row in df.iterrows():
        is_valid, validated_data = validate_row(row)
        while not is_valid:
            row = edit_row(row)
            is_valid, validated_data = validate_row(row)
        print(f"Validated row {index}: {validated_data}")

if __name__ == "__main__":
    main()
