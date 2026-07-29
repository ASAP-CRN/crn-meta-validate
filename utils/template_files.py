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
from typing import Dict, List, Tuple

import pandas as pd
import streamlit as st


# CDE field whose validation value is derived from the organism selection via supported_organisms.
_ORGANISM_ONTOLOGY_FIELD: Tuple[str, str] = ("SAMPLE", "organism_ontology_term_id")


def apply_in_vitro_exclusions(
    cde_dataframe: pd.DataFrame,
    selected_sample_source: str | None,
    in_vitro_sample_sources: List[str],
) -> pd.DataFrame:
    """
    Drop tables or columns from the CDE dataframe when the sample source is in vitro.

    Exclusion rules are driven by the `ExcludeInVitro` column in the CDE dataframe
    (loaded from the CDE spreadsheet). If all fields of a table are flagged, the
    entire table is dropped; otherwise only the flagged fields are dropped.

    Intended to be called in app.py before `build_templates_zip` so the filtered
    dataframe — not the source list — is what crosses the cache boundary.

    Parameters
    ----------
    cde_dataframe : pd.DataFrame
        CDE dataframe to filter. Must contain a `Table` and `Field` column.
        If an `ExcludeInVitro` column is present, rows with value "Exclude" are
        candidates for removal when the sample source is in vitro.
    selected_sample_source : str or None
        User's Step 1 sample-source selection.
    in_vitro_sample_sources : List[str]
        Display labels of sample sources that are considered in vitro
        (loaded from ValidCategories where invitro_source == "Yes").

    Returns
    -------
    pd.DataFrame
        Filtered dataframe, unchanged if `selected_sample_source` is not in vitro
        or if the `ExcludeInVitro` column is absent.
    """
    if not selected_sample_source or selected_sample_source not in in_vitro_sample_sources:
        return cde_dataframe
    if "ExcludeInVitro" not in cde_dataframe.columns:
        return cde_dataframe

    exclude_flag = cde_dataframe["ExcludeInVitro"].astype(str).str.strip().str.lower() == "exclude"

    keep_mask = pd.Series(True, index=cde_dataframe.index)
    for table_name in cde_dataframe["Table"].dropna().unique():
        in_table = cde_dataframe["Table"] == table_name
        table_flagged = exclude_flag & in_table
        if table_flagged.any():
            if table_flagged.sum() == in_table.sum():
                keep_mask &= ~in_table
            else:
                keep_mask &= ~table_flagged

    return cde_dataframe[keep_mask].reset_index(drop=True)


def _is_osa_enum_field(table_name: str, field_name: str, osa_fields: Dict[str, dict]) -> bool:
    """Return True if this (table, field) is one of the OSA enum fields defined in osa_fields."""
    return any(
        spec["table"] == table_name and spec["field"] == field_name
        for spec in osa_fields.values()
    )


def _get_osa_enum_override(
    table_name: str,
    field_name: str,
    osa_fields: Dict[str, dict],
    selected_species: str | None,
    selected_sample_source: str | None,
    selected_assay_type: str | None,
) -> str | None:
    """
    Return the single OSA-selected value for an OSA enum field, or None if "Other".

    Must only be called for fields where `_is_osa_enum_field` returns True.
    Raises ValueError for any other (table, field) combination.

    Parameters
    ----------
    table_name : str
        CDE table name (e.g. "ASSAY", "SAMPLE").
    field_name : str
        CDE field name (e.g. "assay", "sample_source", "organism").
    osa_fields : dict
        OSA field definitions from app_schema (keys: "species", "sample_source", "assay").
    selected_species : str or None
        User's Step 1 organism selection (display label, e.g. "Human").
    selected_sample_source : str or None
        User's Step 1 sample-source selection (display label, e.g. "Brain").
    selected_assay_type : str or None
        User's Step 1 assay key (e.g. "bulk_rna_seq").

    Returns
    -------
    str or None
        The value to use as the sole enum entry, or None when "Other" was
        selected for that axis (keep all enum values).
    """
    axis_to_selected = {
        "species": selected_species,
        "sample_source": selected_sample_source,
        "assay": selected_assay_type,
    }
    for axis_name, spec in osa_fields.items():
        if spec["table"] == table_name and spec["field"] == field_name:
            selected_value = axis_to_selected.get(axis_name)
            if selected_value and selected_value.lower() != "other":
                return selected_value
            return None
    raise ValueError(
        f"_get_osa_enum_override called for non-OSA field: {table_name}.{field_name}"
    )


def _get_organism_ontology_term_id(
    selected_species: str | None,
    supported_organisms: Dict[str, str],
) -> str | None:
    """
    Return the ontology term ID for the selected organism, or None if "Other".

    Parameters
    ----------
    selected_species : str or None
        User's Step 1 organism selection (display label, e.g. "Human").
    supported_organisms : dict
        Mapping of organism display label to ontology term ID
        (e.g. {"Human": "NCBITaxon:9606"}).

    Returns
    -------
    str or None
        The ontology term ID (e.g. "NCBITaxon:9606"), or None when the selected
        organism is "Other" or no selection was made.

    Raises
    ------
    ValueError
        If `selected_species` is a real selection (not "Other") but is absent
        from `supported_organisms`.
    """
    if not selected_species or selected_species.lower() == "other":
        return None
    if selected_species not in supported_organisms:
        raise ValueError(
            f"Organism '{selected_species}' is not in supported_organisms. "
            f"Add it to app_schema cde_definition.supported_organisms or select 'Other'."
        )
    return supported_organisms[selected_species]


@st.cache_data
def build_templates_zip(
    cde_dataframe: pd.DataFrame,
    selected_species: str | None = None,
    selected_sample_source: str | None = None,
    selected_assay_type: str | None = None,
    osa_fields: Dict[str, dict] | None = None,
    supported_organisms: Dict[str, str] | None = None,
) -> tuple[bytes, int]:
    """
    Build a TABLES.zip archive with one comma-delimited template per table.

    In vitro exclusions must be applied to `cde_dataframe` by the caller
    (via `apply_in_vitro_exclusions`) before passing it here, so that the
    already-filtered dataframe is what crosses the cache boundary.

    Parameters
    ----------
    cde_dataframe : pd.DataFrame
        Full CDE dataframe with at least columns:
        ["Table", "Field", "Description", "DataType", "Required", "Validation", "FillNull"]
        Call `apply_in_vitro_exclusions` on this before passing if needed.
    selected_species : str or None
        User's Step 1 organism selection (e.g. "Human"). When not "Other", the
        Validation row for the OSA organism field and SAMPLE.organism_ontology_term_id
        are narrowed to this selection.
    selected_sample_source : str or None
        User's Step 1 sample-source selection (e.g. "Brain"). When not "Other",
        the Validation row for the OSA sample-source field is narrowed to this value.
    selected_assay_type : str or None
        User's Step 1 assay key (e.g. "bulk_rna_seq"). When not "other", the
        Validation row for the OSA assay field is narrowed to this value.
    osa_fields : dict or None
        OSA field definitions from app_schema["cde_definition"]["osa_fields"].
        Keys: "species", "sample_source", "assay"; values: dicts with "table"/"field".
        When None or empty, OSA enum narrowing is skipped.
    supported_organisms : dict or None
        Mapping of organism display label to ontology term ID, from
        app_schema["cde_definition"]["supported_organisms"].
        Used to populate SAMPLE.organism_ontology_term_id.
        When None or empty, ontology term ID narrowing is skipped.

    Returns
    -------
    tuple[bytes, int]
        Bytes of a ZIP archive containing {TABLE}.csv templates, and the number
        of helper rows written per template.
    """
    _osa_fields = osa_fields or {}
    _supported_organisms = supported_organisms or {}

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
                for field_name, data_type, raw_validation in zip(field_names, data_types, validation_values):
                    is_enum = str(data_type).strip().lower() == "enum"

                    # organism_ontology_term_id: inherit value from organism selection
                    if (table_name, field_name) == _ORGANISM_ONTOLOGY_FIELD:
                        ontology_val = _get_organism_ontology_term_id(
                            selected_species, _supported_organisms
                        )
                        if ontology_val is not None:
                            validation_row.append(str([ontology_val]))
                        elif is_enum:
                            validation_row.append(str(raw_validation) if not pd.isna(raw_validation) else "[]")
                        else:
                            validation_row.append(f"Validation:{data_type}")

                    # OSA enum fields: narrow to the user's direct OSA selection
                    elif is_enum and _osa_fields and _is_osa_enum_field(table_name, field_name, _osa_fields):
                        osa_value = _get_osa_enum_override(
                            table_name, field_name, _osa_fields,
                            selected_species, selected_sample_source, selected_assay_type,
                        )
                        if osa_value is not None:
                            # Narrow enum to the user's OSA selection
                            validation_row.append(str([osa_value]))
                        elif pd.isna(raw_validation):
                            validation_row.append("[]")
                        else:
                            validation_row.append(str(raw_validation))

                    # All other enum fields: keep the full CDE enum list
                    elif is_enum:
                        if pd.isna(raw_validation):
                            # Fallback in the unlikely case of a missing Validation for an Enum
                            validation_row.append("[]")
                        else:
                            validation_row.append(str(raw_validation))

                    # Non-Enum columns get a simple "Validation:{DataType}" marker
                    else:
                        validation_row.append(f"Validation:{data_type}")

                # Build the CSV content in memory
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
