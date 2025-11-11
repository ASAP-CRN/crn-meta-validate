"""
Validate tables utilities for ASAP CRN metadata QC app

This module checks for handles loading and processing of CDE definitions from either
Google Sheets or local CSV files.
"""

import pandas as pd

# wrape this in try/except to make using the ReportCollector portable
# probably an abstract base class would be better
try:
    import streamlit as st
    print("Streamlit imported successfully")

except ImportError:
    class DummyStreamlit:
        @staticmethod
        def markdown(self,msg):
            pass
        def error(self,msg):
            pass
        def header(self,msg):
            pass        
        def subheader(self,msg):
            pass    
        def divider(self):
            pass
    st = DummyStreamlit()
    print("Streamlit NOT successfully imported")

NULL = "NA"

def get_log(log_file):
    """ grab logged information from the log file."""
    with open(log_file, 'r') as f:
        report_content = f.read()
    return report_content

def columnize( itemlist ):
    NEWLINE_DASH = ' \n- '
    if len(itemlist) > 1:
        return f"- {itemlist[0]}{NEWLINE_DASH.join(itemlist[1:])}"
    else:
        return f"- {itemlist[0]}"
    
def read_meta_table(table_path):
    # read the whole table
    try:
        table_df = pd.read_csv(table_path,dtype=str)
    except UnicodeDecodeError:
        table_df = pd.read_csv(table_path, encoding='latin1',dtype=str)

    # drop the first column if it is just the index
    if table_df.columns[0] == "Unnamed: 0":
        table_df = table_df.drop(columns=["Unnamed: 0"])
        
    table_df.replace({"":NULL, pd.NA:NULL, "none":NULL, "nan":NULL, "Nan":NULL}, inplace=True)

    return table_df


class ReportCollector:
    """
    Class to collect and log messages, errors, and markdown to a log file and/or streamlit
    """

    def __init__(self, destination="both"):
        self.entries = []
        self.filename = None

        if destination in ["both", "streamlit"]:
            self.publish_to_streamlit = True
        else:
            self.publish_to_streamlit = False

    def add_markdown(self, msg):
        self.entries.append(("markdown", msg))
        if self.publish_to_streamlit:
            st.markdown(msg)

    def add_success(self, msg):
        self.entries.append(("success", msg))
        if self.publish_to_streamlit:
            st.success(msg)

    def add_error(self, msg):
        self.entries.append(("error", msg))
        if self.publish_to_streamlit:
            st.error(msg)

    def add_warning(self, msg):
        self.entries.append(("warning", msg))
        if self.publish_to_streamlit:
            st.warning(msg)

    def add_header(self, msg):
        self.entries.append(("header", msg))
        if self.publish_to_streamlit:    
            st.header(msg)

    def add_subheader(self, msg):
        self.entries.append(("subheader", msg))
        if self.publish_to_streamlit:    
            st.subheader(msg)

    def add_divider(self):
        self.entries.append(("divider", None))
        if self.publish_to_streamlit:    
            st.divider()

    
    def write_to_file(self, filename):
        self.filename = filename
        with open(filename, 'w') as f:
            report_content = self.get_log()
            f.write(report_content)
    

    def get_log(self):
        """ grab logged information from the log file."""
        report_content = []
        for msg_type, msg in self.entries:
            if msg_type == "markdown":
                report_content += f"{msg}\n"
            elif msg_type == "error":
                report_content += f"{msg}\n"
            elif msg_type == "header":
                report_content += f"# {msg}\n"
            elif msg_type == "subheader":
                report_content += f"## {msg}\n"
            elif msg_type == "divider":
                report_content += 60*'-' + '\n'
        
        return "".join(report_content)

    def reset(self):
        self.entries = []
        self.filename = None

    def print_log(self):
        print(self.get_log())

def validate_table(df: pd.DataFrame, table_name: str, specific_cde_df: pd.DataFrame, out: ReportCollector ):
    """
    Validate the table against the specific table entries from the CDE
    """
    def my_str(x):
        return f"'{str(x)}'"
        
    missing_required = []
    missing_optional = []
    null_columns = []
    invalid_entries = []
    total_rows = df.shape[0]
    for column in specific_cde_df["Field"]:
        entry_idx = specific_cde_df["Field"]==column

        opt_req = "REQUIRED" if specific_cde_df.loc[entry_idx, "Required"].item()=="Required" else "OPTIONAL"

        if column not in df.columns:
            if opt_req == "REQUIRED":
                missing_required.append(column)
            else:
                missing_optional.append(column)

            # print(f"missing {opt_req} column {column}")

        else:
            datatype = specific_cde_df.loc[entry_idx,"DataType"]
            if datatype.item() == "Integer":
                print(f"recoding {column} as int")
                df.replace({"Unknown":NULL, "unknown":NULL}, inplace=True)
                try:
                    df[column].apply(lambda x: int(x) if x!=NULL else x )
                except Exception as e:
                    invalid_values = df[column].unique()
                    n_invalid = invalid_values.shape[0]
                    valstr = "int or NULL ('NA')"
                    invalstr = ', '.join(map(my_str,invalid_values))
                    invalid_entries.append((opt_req, column, n_invalid, valstr, invalstr))

                # test that all are integer or NULL, flag NULL entries
            elif datatype.item() == "Float":
                df.replace({"Unknown":NULL, "unknown":NULL}, inplace=True)
                try:
                    df[column] = df[column].apply(lambda x: float(x) if x!=NULL else x )
                except Exception as e:
                    invalid_values = df[column].unique()
                    n_invalid = invalid_values.shape[0]
                    valstr = "float or NULL ('NA')"
                    invalstr = ', '.join(map(my_str,invalid_values))
                    invalid_entries.append((opt_req, column, n_invalid, valstr, invalstr))
            elif datatype.item() == "Enum":
                valid_values = eval(specific_cde_df.loc[entry_idx,"Validation"].item())
                valid_values += [NULL]
                entries = df[column]
                valid_entries = entries.apply(lambda x: x in valid_values)
                invalid_values = entries[~valid_entries].unique()
                n_invalid = invalid_values.shape[0]
                if n_invalid > 0:
                    valstr = ', '.join(map(my_str, valid_values))
                    invalstr = ', '.join(map(my_str,invalid_values))
                    invalid_entries.append((opt_req, column, n_invalid, valstr, invalstr))
            else: #dtype == String
                pass
            
            n_null = (df[column]==NULL).sum()
            if n_null > 0:            
                null_columns.append((opt_req, column, n_null))


    # now compose report...
    if len(missing_required) > 0:
        out.add_error(f"Missing required columns in {table_name}: {', '.join(missing_required)}")
        for column in missing_required:
            df[column] = NULL

    else:
        out.add_success(f"OK -- All required columns are present in *{table_name}* table.")

    if len(missing_optional) > 0:
        out.add_error(f"ERROR -- Missing optional columns in {table_name}: {', '.join(missing_optional)}")
        for column in missing_optional:
            df[column] = NULL

    if len(null_columns) > 0:
        out.add_error(f"ERROR -- {len(null_columns)} columns with empty (NULL) values:")
        for opt_req, column, count in null_columns:
            out.add_markdown(f"\n\t- {column}: {count}/{total_rows} empty rows ({opt_req})")
    else:
        out.add_success(f"OK -- No empty values (NULL) found\n")

    if len(invalid_entries) > 0:
        out.add_error(f"ERROR -- {len(invalid_entries)} columns with invalid values:")
        for opt_req, column, count, valstr, invalstr in invalid_entries:
            str_out = f"- Column _*{column}*_ has invalid values: {invalstr}\n"
            str_out += f"    - expect: {valstr}\n"
            out.add_markdown(str_out)
    else:
        out.add_success(f"No invalid values found in Enum columns\n")

    for column in df.columns:
        if column not in specific_cde_df["Field"].values:
            out.add_warning(f"Extra column in {table_name}: {column}")

    return df, out
