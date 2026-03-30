# ASAP CRN Metadata QC App

<!-- DOCS_INTRO_START -->

This app assists data contributors to QC their metadata tables in comma-delimited format (e.g. STUDY.csv, SAMPLE.csv, PROTOCOL.csv, etc.) before uploading them to ASAP CRN Google buckets.

We do this in five steps:     
**Step 1. Indicate your Dataset type:** the app will determine expected CSV files and columns.     
**Step 2. Download template files:** a left-side bar will appear indicating expected files and providing file templates.     
**Step 3. Fill out and upload files:** offline, fill out files with your metadata and upload them via the Drag & drop box or Browse button.     
**Step 4. Fix common issues:** follow app instructions to fix common issues (e.g. non-comma delimiters and missing values).     
**Step 5. CDE validation:** the app reports missing columns and value mismatches vs. the [ASAP CRN controlled vocabularies (CDE) v4.2](https://docs.google.com/spreadsheets/d/1c0z5KvRELdT2AtQAH2Dus8kwAyyLrR0CROhKOjpU4Vc/edit?usp=sharing).

Two types of issues will be reported:     
**Errors (❌):**  must be fixed by the data contributors before uploading metadata to ASAP CRN Google buckets.     
**Warnings (⚠️):** recommended to be fixed before uploading, but not required.     

Free text boxes allow users to record per-column comments to provide context to data curators during review.

<!-- DOCS_INTRO_END -->

## The five steps at a glance

| Step | What you do | What the app does |
|------|-------------|-------------------|
| **1. Dataset setup** | Select species, sample source, and assay type | Determines which CSV files and columns are expected |
| **2. Download templates** | Download a zip of template CSV files | Provides column headers, descriptions, and valid values |
| **3. Upload files** | Fill out templates offline, then upload | Loads your files into the app for checking |
| **4. Fix common issues** | Follow app instructions | Detects delimiter problems and missing values |
| **5. CDE validation** | Click Compare vs. CDE | Reports errors and warnings against controlled vocabularies |

## Two types of issues

- **Errors (❌)** — must be fixed before uploading to Google buckets
- **Warnings (⚠️)** — recommended to fix, but not required

## Go to the app

👉 **[Open the QC App](https://asap-meta-qc.streamlit.app/)**

---

For questions or to report a bug, email [support@dnastack.com](mailto:support@dnastack.com) or open a [GitHub issue](https://github.com/ASAP-CRN/crn-meta-validate/issues).
