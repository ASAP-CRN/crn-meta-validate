# imports
import pandas as pd

# wrape this in try/except to make suing the ReportCollector portable
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
    print("Streamlit NOT successfully")


class ReportCollector:
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


    def add_error(self, msg):
        self.entries.append(("error", msg))
        if self.publish_to_streamlit:
            st.error(msg)

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
                report_content += msg + '\n'
            elif msg_type == "error":
                report_content += f"🚨⚠️❗ **{msg}**\n"
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
    
# Function to read a table with the specified data types
def read_meta_table(table_path,dtypes_dict):
    # read the whole table
    try:
        table_df = pd.read_csv(table_path,dtype=dtypes_dict)
    except UnicodeDecodeError:
        table_df = pd.read_csv(table_path, encoding='latin1',dtype=dtypes_dict)

    # drop the first column if it is just the index
    if table_df.columns[0] == "Unnamed: 0":
        table_df = table_df.drop(columns=["Unnamed: 0"])
    return table_df



# Function to get data types dictionary for a given table
def get_dtypes_dict(cde_df):
    # unnescessary.
    # # Filter the CDE data frame to get the fields and data types for the specified table
    # table_cde = cde_df[cde_df["Table"] == table_name]
    
    # Initialize the data types dictionary
    dtypes_dict = {}
    
    # Iterate over the rows to fill the dictionary
    for _, row in cde_df.iterrows():
        field_name = row["Field"]
        data_type = row["DataType"]
        
        # Set the data type to string for "String" and "Enum" fields
        if data_type in ["String"]:
            dtypes_dict[field_name] = 'string'
        elif data_type == "Enum":
            dtypes_dict[field_name] = 'category'
        elif data_type == "Integer":
            dtypes_dict[field_name] = 'Int64'  # nullable integer
        elif data_type == "Float":
            dtypes_dict[field_name] = 'float64'  # nullable float
    
    return dtypes_dict


# Function to get data types dictionary for a given table
def get_dtypes_dict_all(cde_df):
    # Initialize the data types dictionary
    dtypes_dict = {}
    
    # Iterate over the rows to fill the dictionary
    for _, row in cde_df.iterrows():
        field_name = row["Field"]
        data_type = row["DataType"]
        
        # Set the data type to string for "String" and "Enum" fields
        if data_type in ["String"]:
            dtypes_dict[field_name] = 'string'
        elif data_type == "Enum":
            dtypes_dict[field_name] = 'category'
        elif data_type == "Integer":
            dtypes_dict[field_name] = 'Int64'  # nullable integer
        elif data_type == "Float":
            dtypes_dict[field_name] = 'Float64'  # nullable float
    
    return dtypes_dict

# streamlit specific helpers which don't depend on streamlit

def load_css(file_name):
   with open(file_name) as f:
      st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

