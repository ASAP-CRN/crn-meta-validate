"""
Template file generation utilities for ASAP CRN metadata QC app.

This module builds a ZIP archive containing one comma-delimited template file
per CDE table. Each template file is named {TABLE}.csv and contains six rows:

- Row 1: CDE "Field" values
- Row 2: CDE "Description" values
- Row 3: CDE "DataType" values
- Row 4: CDE "Required" values
- Row 5: For Enum columns, the "Validation" field (Python list literal);
         for non-Enum columns, the string "Validation:{DataType}".
- Row 6: CDE "FillNull" values

Users can use these templates as a starting point to fill in their metadata.
Before uploading the completed tables back into the app, they should remove
rows 2–6 so that only row 1 (field names) remains as the header.
"""

from __future__ import annotations

import csv
from io import StringIO, BytesIO
from typing import List

import pandas as pd
import streamlit as st


@st.cache_data
def build_templates_zip(cde_dataframe: pd.DataFrame) -> bytes:
    """
    Build a TABLES.zip archive with one comma-delimited template per table.

    Parameters
    ----------
    cde_dataframe : pd.DataFrame
        Full CDE dataframe with at least columns:
        ["Table", "Field", "Description", "DataType", "Required", "Validation", "FillNull"]

    Returns
    -------
    bytes
        Bytes of a ZIP archive containing {TABLE}.csv templates.
    """
    zip_buffer = BytesIO()
    
    # Use a deterministic order for reproducibility
    unique_tables: List[str] = sorted(
        table_name for table_name in cde_dataframe["Table"].dropna().unique()
    )

    with st.spinner("Preparing template files (TABLES.zip)..."):
        import zipfile

        with zipfile.ZipFile(zip_buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as zip_file:
            for table_name in unique_tables:
                table_cde = (
                    cde_dataframe[cde_dataframe["Table"] == table_name]
                    .reset_index(drop=True)
                )

                # Extract core rows
                field_names = table_cde["Field"].astype(str).tolist()
                descriptions = table_cde["Description"].astype(str).tolist()
                data_types = table_cde["DataType"].astype(str).tolist()
                required_flags = table_cde["Required"].astype(str).tolist()
                validation_values = table_cde["Validation"].tolist()
                fill_null_values = table_cde["FillNull"].astype(str).tolist()

                validation_row: List[str] = []
                for data_type, raw_validation in zip(data_types, validation_values):
                    # Enum columns use their Validation value (Python list literal in the CDE)
                    if str(data_type).strip().lower() == "enum":
                        if pd.isna(raw_validation):
                            # Fallback in the unlikely case of a missing Validation for an Enum
                            validation_row.append("[]")
                        else:
                            validation_row.append(str(raw_validation))
                    else:
                        # Non-Enum columns get a simple "Validation:{DataType}" marker
                        validation_row.append(f"Validation:{data_type}")

                # Build the TSV content in memory
                string_buffer = StringIO()
                writer = csv.writer(string_buffer, delimiter=",", lineterminator="\n")

                rows_to_write = [
                    field_names,
                    descriptions,
                    data_types,     
                    required_flags,
                    validation_row,
                    fill_null_values,
                ]
                number_of_rows = len(rows_to_write)
                for row in rows_to_write:
                    writer.writerow(row)

                csv_content = string_buffer.getvalue().encode("utf-8")
                csv_name = f"{table_name}.csv"

                zip_file.writestr(csv_name, csv_content)

    # Seek back to the beginning and return raw bytes
    zip_buffer.seek(0)
    return zip_buffer.getvalue(), number_of_rows
