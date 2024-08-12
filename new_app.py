import pandas as pd
from pydantic import BaseModel, constr, conint, confloat, ValidationError, create_model
from enum import Enum
import re

# Load the CDE file
file_path = 'ASAP_CDE_v2.1.csv'
cde_df = pd.read_csv(file_path)

cde_df = cde_df[cde_df['Table'] == 'CLINPATH']

cde_df.head()

# Create a dictionary to hold dynamically created Enums
enums_dict = {}

# Function to create Enum classes dynamically
def create_enum(field_name, values):
    enum_name = f"{field_name}Enum"
    enums_dict[enum_name] = Enum(enum_name, {v: v for v in values})
    return enums_dict[enum_name]

# Prepare a dictionary for dynamically creating the Pydantic model
model_fields = {}

for index, row in cde_df.iterrows():
    field_name = row['Field']
    data_type = row['DataType']
    validation = row['Validation']
    
    if data_type == 'Enum' and pd.notna(validation):
        # Extract enum values from the validation field
        enum_values = re.findall(r'"(.*?)"', validation)
        enum_class = create_enum(field_name, enum_values)
        model_fields[field_name] = (enum_class, ...)
    elif data_type == 'String':
        model_fields[field_name] = (constr(strict=True, min_length=1), ...)
    elif data_type == 'Integer':
        model_fields[field_name] = (conint(strict=True), ...)
    elif data_type == 'Float':
        model_fields[field_name] = (confloat(strict=True), ...)
    else:
        model_fields[field_name] = (str, ...)

# Dynamically create the Pydantic model
DynamicDataRow = create_model('DynamicDataRow', **model_fields)

# Function to validate a row of data
def validate_row(row):
    try:
        data_row = DynamicDataRow(**row.to_dict())
        return True, data_row
    except ValidationError as e:
        print(f"Validation error: {e}")
        return False, None

# Function to interactively edit a row
def edit_row(row):
    print("Please edit the invalid entries:")
    for col in row.index:
        new_value = input(f"Enter a valid value for {col} (current: {row[col]}): ")
        row[col] = new_value
    return row

# Main function to load CSV data and validate it
def main():
    data_file_path = '../meta-clean/ASAP_tables/TEAM-LEE/CLINPATH.csv'  # Replace with your data file path
    df = pd.read_csv(data_file_path)

    for index, row in df.iterrows():
        is_valid, validated_data = validate_row(row)
        while not is_valid:
            row = edit_row(row)
            is_valid, validated_data = validate_row(row)
        print(f"Validated row {index}: {validated_data}")

if __name__ == "__main__":
    main()
