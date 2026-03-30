# Changelog

All notable changes to this project are documented here.

Format: `Webapp vX.Y (CDE vZ) — Date`

---

## v0.9.2 — 02 March 2026 · CDE v4.2 (optional v3.4)

- Add `AssayInstrumentTechnology` (AIT) tab to automate definition of instruments and technologies used in each assay, reducing manual work for users
- Add CDE synchronization evaluation of `CDE_current` vs. AIT tabs
- Add `load_and_validate_schema` function to encapsulate all app configuration from JSON and Google Sheets for public consumption

## v0.9.1 — 27 February 2026 · CDE v4.2 (optional v3.4)

- Update to CDE version v4.2 (including fields for ATAC and Proteomics assays)
- Add CDE column `AllowMultiEnum` and functionality to allow multiple Enum values for specific fields (e.g. multiple brain regions per sample)

## v0.9 — 04 February 2026 · CDE v4.2 (optional v3.4)

- Remove `table_categories` from `app_schema.json` — now loaded from CDE Spreadsheet `ValidCategories` tab

## v0.8 — 02 February 2026 · CDE v4.1 (optional v3.4)

- Fix bug not using `Specific[Species|SampleSource|Assay]` filters when building template files and validating tables
- Slim down coloured logs and direct users to "see below" sections for details on missing columns and invalid values
- Add free-text box for "Other" entries in Step 1 dropdowns

## v0.7 — 20 January 2026 · CDE v4.0 (optional v3.4)

- Fix bug accepting malformed Pandas dataframes
- Allow switching between CDE versions for Step 5 validation (if enabled in `app_schema`)

## v0.6 — 01 December 2025 · CDE v4.0

- Update to CDE version v4.0
- Use Assay Type for the dropdown menu instead of Modality
- Provide template files as a zipped download in the Expected files section
- Add free-text box for user comments on each column (included in final report)
- Make dropdown menus searchable
- Standardize logs, documentation and aesthetics across the app
- Add colours to final table preview based on missing values and invalid vs. CDE status

## v0.5 — 25 November 2025 · CDE v3.4

- Assist users to fill out missing values on each column via radio buttons, free text, or dropdown menus
- Improve detection of missing values in `utils/find_missing_values.py`
- Compare each column vs. CDE using both Validation and FillNull rules
- Add download button for pre-CDE-validated sanitized CSV

## v0.4 — 13 November 2025 · CDE v3.3-beta

- CDE version is now provided in `resource/app_schema_{webapp_version}.json` and loaded via `utils/cde.py`
- Add supported species, assay, and sample source dropdowns to select expected tables
- Add reset button to sidebar (resets cache and file uploader)
- Add `app_schema` to manage app configuration
- Add `DelimiterHandler` and `ProcessedDataLoader` classes to `utils/`
- Improve delimiter detection
- Improve file upload handling and status display

## v0.3 — 01 April 2025 · CDE v3

*(No detailed notes recorded)*

## v0.2 — 20 August 2023 · CDE v2

*(Initial release)*
