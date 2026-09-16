# ASAP CRN metadata QC app at a glance

<!-- DOCS_INTRO_START -->

This app assists data contributors to QC their metadata tables in comma-delimited format (e.g. STUDY.csv, SAMPLE.csv, PROTOCOL.csv, etc.) against the ASAP CRN controlled vocabularies (CDE) before uploading them to Google buckets.

<!-- DOCS_INTRO_END -->

We do this in five steps:

<!-- DOCS_STEPS_TABLE_START -->

| Step | What you do | What the app does |
|------|-------------|-------------------|
| **1. Dataset setup** | Select species, sample source, and assay type | Determines which CSV files and columns are expected |
| **2. Download templates** | Download a zip of template CSV files | Provides column headers, descriptions, and valid values |
| **3. Upload files** | Fill out templates offline, then upload | Loads your files into the app for checking |
| **4. Fix common issues** | Follow app instructions | Helps to fix delimiter problems and missing values |
| **5. CDE validation** | Click Compare vs. CDE | Reports errors and warnings against the [CDE v4.5](https://docs.google.com/spreadsheets/d/1c0z5KvRELdT2AtQAH2Dus8kwAyyLrR0CROhKOjpU4Vc/edit?usp=sharing) |

<!-- DOCS_STEPS_TABLE_END -->

<!-- DOCS_TWO_TYPES_START -->

Two types of issues will be reported:

- **Errors (❌)** — must be fixed by the data contributors before uploading metadata to ASAP CRN Google buckets.
- **Warnings (⚠️)** — recommended to be fixed before uploading, but not required.

<!-- DOCS_TWO_TYPES_END -->

Free text boxes allow users to record per-column comments to provide context to data curators during review.


## 📖 **[Full step-by-step user guide](https://asap-crn.github.io/crn-meta-validate/user-guide/step1-dataset-setup/)**
Includes all five steps with screenshots, a [FAQ](https://asap-crn.github.io/crn-meta-validate/faq/), and download instructions. Example CSV files to test the app are available [here](https://github.com/ASAP-CRN/crn-meta-validate/tree/main/resource/tester_files).

## 👉 **[Go to the app](https://asap-meta-qc.streamlit.app/)**

---

For questions or to report a bug, email [support@dnastack.com](mailto:support@dnastack.com) or open a [GitHub issue](https://github.com/ASAP-CRN/crn-meta-validate/issues).
