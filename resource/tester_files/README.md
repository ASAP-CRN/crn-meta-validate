## Metadata validator for ASAP CRN metadata (v0.5) test infiles

#### DATA.csv
* This file is labeled as csv file but it actually is semicolon-delimited. The app can handle comma-, semicolon- and tab-delimited files.
* A warning on column `batch` not being part of the CDE and hence not being evaluated will be produced
* After filling out missing values and comparing vs. the CDE v3.3, the log will produce the following Error:
  * Required column adjustment has 1 invalid values    
    Invalid values: 'quality trimmed and human DNA removed'     
    Expected: 'Processed', 'Unknown', 'Raw', 'NA', 'Not Reported'     
* The _data contributors_ would need to either:
  * Download the _DATA_ file from _Step 2_ (i.e. after filling out missing values) and replace invalid values (i.e. not matching the CDE controlled vocabularies), or
  * Communicate to DNAstack data curators that invalid values are actually correct and upload the file from Step 2 to the dataset Google bucket.

#### PROTOCOL.csv
* This file is labeled as csv file but it actually is semicolon-delimited. The app can handle comma-, semicolon- and tab-delimited files.
* After filling out missing values and comparing vs. the CDE v3.3, the log will produce no errors.
* The User can download file PROTOCOL_after_cde_comparison.csv, change name to PROTOCOL.csv and upload it to the dataset Google bucket.

#### SAMPLE.csv and STUDY.csv
* These are actually csv files.
* After filling out each file's missing values and comparing them vs. the CDE v3.3, the log will produce no errors.
* The User can download each *after_cde_comparison.csv file, change their name to SAMPLE.csv and STUDY.csv and upload it to the dataset Google bucket.

#### SUBJECT.csv
* This file has only column headers and hence will be flagged to skip validation.
