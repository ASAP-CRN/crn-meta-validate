## Metadata validator for ASAP CRN metadata test infiles

These files are based on the structure of the CDE v4.1 tables.

---

#### DATA.csv
* This file is **semicolon-delimited**. The app can handle comma-, semicolon-, and tab-delimited files.
* A warning on column `gcp_bucket` not being part of the CDE and hence not being evaluated will be produced.
* After filling out missing values and comparing vs. CDE v4.1, the log will produce the following **Error**:
  * Required column `adjustment` has 1 invalid value
    * Invalid value: `'corrected and normalized'` (which is not one of the expected values for this column)
    * Expected: `'Raw'`, `'Processed'`
* The _data contributors_ would need to either:
  * Download the _DATA_ file from _Step 4_ (i.e. after filling out missing values) and replace the invalid value, or
  * Communicate to ASAP CRN data curators that the value is intentional and upload the _Step 4_ file to the dataset Google bucket.

---

#### PROTOCOL.csv
* This file is **semicolon-delimited**. The app can handle comma-, semicolon-, and tab-delimited files.
* After filling out missing values and comparing vs. CDE v4.1, the log will produce **no errors**.
* The user can download `PROTOCOL_after_cde_comparison.csv`, rename it to `PROTOCOL.csv`, and upload it to the dataset Google bucket.

---

#### SAMPLE.csv
* This is a **comma-delimited** CSV file.
* All columns are filled out with 'NA' when data is not available
* After filling out missing values and comparing vs. CDE v4.1, the log will produce the following **Error**:
  * Required column `condition_id` has 2 invalid values
    * Invalid value: `'IBD'`
    * Expected: `'PD'`, `'Control'`, `'Prodromal'`, `'Other'`
* The _data contributors_ would need to replace the invalid `condition_id` values (e.g., `'IBD'` → `'Other'`), or
  Communicate to ASAP CRN data curators that the value is intentional and upload the _Step 4_ file to the dataset Google bucket.
* Note: that for column `region_level_1`, two region annotations are provided semi-colon delimited, which is allowed:
  * `Substantia nigra pars dorsalis (SND, UBERON:0002038);Substantia nigra pars medialis (SNM, UBERON:0002038)`    

---

#### SUBJECT.csv
* This file has **only column headers** and hence will be flagged to skip validation.

---

#### CLINPATH.csv
* This file has **26 fields in row 4** (subject_3), but only **29 fields in the header**, which leads to a **parsing error**.
  * Specifically, row 4 has an extra spurious field `ExtraField` appended, causing the field count to mismatch.
  * The _data contributors_ would need to fix row 4 offline and input the new file for validation.
