# crn-meta-validate
Metadata validator for ASAP CRN metadata (v0.6)

<!-- PROJECT SHIELDS -->
<!--
*** We are using markdown "reference style" links for readability.
*** Reference links are enclosed in brackets [ ] instead of parentheses ( ).
*** See the bottom of this document for the declaration of the reference variables
*** for contributors-url, forks-url, etc. This is an optional, concise syntax you may use.
*** https://www.markdownguide.org/basic-syntax/#reference-style-links
-->

<!-- PROJECT HEADER -->
<br />
<div align="center">

  <h3 align="center">ASAP CRN Cloud Platform metadata quality control (QC) app</h3>

  <p align="center">
    An app that allows you to QC your metadata before uploading it to Google buckets
    <br />
    <br />
  </p>
</div>

<!-- TABLE OF CONTENTS -->
<details>
  <summary>Table of Contents</summary>
  <ol>
    <li><a href="#about-the-app">About the app</a></li>
    <li><a href="#how-to-use-the-web-app">How to use the web app</a></li>
    <li><a href="#for-developers">For developers</a>
    <ul>
      <li><a href="#prerequisites">Prerequisites</a></li>
      <li><a href="#installation">Installation</a></li>
      <li><a href="#contributing">Contributing</a></li>
    </ul>
    <li><a href="#contact-report-bugs-and-request-features">Contact, report bugs and request features</a></li>
    <li><a href="#authors">Authors</a></li>
    <li><a href="#acknowledgments">Acknowledgments</a></li>
    <li><a href="#license">License</a></li>
  </ol>
</details>

<!-- ABOUT THE APP -->
## About the app

<!-- APP_INTRO_START -->

This app assists data contributors to QC their metadata tables in comma-delimited format (e.g. STUDY.csv, SAMPLE.csv, PROTOCOL.csv, etc.) before uploading them to ASAP CRN Google buckets.

We do this in five steps:     
**Step 1. Indicate your Dataset type:** the app will determine expected CSV files and columns.     
**Step 2. Download template files:** a left-side bar will appear indicating expected files and providing file templates.     
**Step 3. Fill out and upload files:** offline, fill out files with your metadata and upload them via the Drag & drop box or Browse button.     
**Step 4. Fix common issues:** follow app instructions to fix common issues (e.g. non-comma delimiters and missing values).     
**Step 5. CDE validation:** the app reports missing columns and value mismatches vs. the [ASAP CRN controlled vocabularies (CDE) v4.0](https://docs.google.com/spreadsheets/d/1c0z5KvRELdT2AtQAH2Dus8kwAyyLrR0CROhKOjpU4Vc/edit?usp=sharing).

Two types of issues will be reported:     
**Errors (❌):**  must be fixed by the data contributors before uploading metadata to ASAP CRN Google buckets.     
**Warnings (⚠️):** recommended to be fixed before uploading, but not required.     

Free text boxes allow users to record per-column comments to provide context to data curators during review.


<!-- APP_INTRO_END -->

<p align="right">(<a href="#crn-meta-validate">back to top</a>)</p>

<!-- GETTING STARTED / WEB APP -->
## How to use the web app

#### Go to the [web app URL](https://asap-meta-qc.streamlit.app/)     
#### Step 1 -- Set up your run:   
  * In the dropdown menus, specify the following properties for your Dataset:    
    * `Species`    
    * `Tissue/Cell origin`   
    * `Assay type`    
#### Step 2 -- A left-side menu will appear, including:
  * A button to download a *zip file with `template CSV files` for your Dataset
  * Each CSV file will have six rows:      
    1. Column headers      
    2. Column descriptions      
    3. Column data types. One of four types:      
          - Integer (numeric, e.g. 0, 1, 2, 3, etc.)      
          - Float (numeric, e.g. 0.1, 1.2, 10.1, etc.)      
          - String (free form text)      
          - Enum (controlled vocabularies, see Validation vs. the CDE below)      
    4. Column required status      
          - Required (mandatory columns)      
          - Optional (optional columns)      
    5. Column validation rules      
          - For Enum data type, provides a list of valid values      
          - For non-Enum data types, validation only requires to match data type
    6. Values to fill out Column
          - Valid values to fill out missing values
#### Step 3 -- Upload your Dataset CSV files
  * We encourage users to fill out the CSV templates programatically to avoid typos and Excel issues handling date-like strings, etc.
  * If you used the template files from Step 2, remove the helper rows 2 to 6 (i.e. keep only the Column headers and your actual Dataset metadata).
  * Once filled out, upload your CSV files via the `Drag & drop box` or the `Browse button`.
  * Each of your CSV files will become a `TABLE` in the app memory.
#### Step 4 -- Fix common issues
  * Follow the app instructions to `fix common issues`, (e.g non-comma delimiters and missing values).     
  * For each colum with missing values, a free text box is provided to `Record comments` for ASAP curators.    
#### Step 5 -- Validate vs. the CDE
  * Compare each `TABLE` vs. the [ASAP CRN controlled vocabularies (CDE)](https://docs.google.com/spreadsheets/d/1c0z5KvRELdT2AtQAH2Dus8kwAyyLrR0CROhKOjpU4Vc/edit?usp=sharing).
  * The app will report missing columns and value mismatches vs. the CDE.
  * A log for each `TABLE column` will be provided, including:
    * ✅ **Successful** steps.    
    * ❌ **Errors** to be fixed by _data contributors_ before uploading the CSV file to ASAP Google Cloud buckets.   
    * ⚠️ **Warnings** which the authors may opt to fix or not, depending on the dataset experiment configuration.   
  * For each colum with CDE validation issues, a free text box is provided to `Record comments` for ASAP curators.    
  * At the end, three files can be downloaded:
    * A `TABLE.md` markup file with each `TABLE` run report.   
    * A `TABLE_comments.md` markup file with user column-level comments that can be provided to ASAP curators.   
    * A sanitized `TABLE.cde_compared.csv` file. Note: button will be enabled only if no errors were found. You can upload this file to its Google bucket (see [Notes](#notes)).

### Notes:
* If you have multiple datasets to validate, complete steps 1 to 5 for each Dataset separately.     
* Upload your final files to the Google bucket following [these instructions](https://docs.google.com/document/d/1Bicp20M0Zi_dc2-4nQJZwOCy5E20LJte0wT9pgKeVag/edit?usp=sharing).     
* Once you've completed uploading your metadata, raw data, and artifacts to the Google bucket, inform our [data manager](matthieu.darracq@dnastack.com). We will notify you if any issues are found.     
* We are here to help. [Contact us](#contact-report-bugs-and-request-features) if you have questions.    
* Example CSV files to test the app can be downloaded from [here](https://github.com/ASAP-CRN/crn-meta-validate/tree/Update_Streamlit_NewModalties_and_UX/resource/tester_files).

<p align="right">(<a href="#crn-meta-validate">back to top</a>)</p>

<!-- FOR DEVELOPERS -->
## For developers
*_To run this app locally_*

### Prerequisites
* Docker
* Python v3.11 or higher

### Installation 
1. Clone the github repository
```bash
git clone git@github.com:ASAP-CRN/crn-meta-validate.git
```

2. Make sure that you have access to the CDE spreadsheet, link provided in `utils/cde.py`

3. Build the docker container that contains the app
```bash
docker build -t <docker-container-name> .
```

4. Run the docker container on a port
```bash
docker run -d -p 8080:8080 <docker-container-name>
```

5. Alternatively, you can also build virtual environment, then run the streamlit app locally
```bash
streamlit run app.py
```

### Contributing
Contributions are what make the open source community such an amazing place to learn, inspire, and create. Any contributions you make are **greatly appreciated**. If you have a suggestion that would make this better, please do this and thanks again!
1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

<p align="right">(<a href="#crn-meta-validate">back to top</a>)</p>

<!-- CONTACT, REPORT BUGS AND REQUEST FEATURES -->
## Contact, report bugs and request features
- Please use these templates to report bugs or request features:    
  https://github.com/ASAP-CRN/crn-meta-validate/tree/main/.github/ISSUE_TEMPLATE
- Email your report/request to [support@dnastack.com](support@dnastack.com)

<p align="right">(<a href="#crn-meta-validate">back to top</a>)</p>

<!-- AUTHORS -->
## Authors
- [Andy Henrie](https://github.com/ergonyc)
- [Javier Diaz](https://github.com/jdime)

<p align="right">(<a href="#crn-meta-validate">back to top</a>)</p>

<!-- ACKNOWLEDGMENTS -->
## Acknowledgments
This would not be possible without help of the Data Tecnica team, specially Alejandro Martinez, and the similar GP2 tool.
* [DtI](https://www.datatecnica.com/)
* [ASAP CRN](https://parkinsonsroadmap.org/)

<p align="right">(<a href="#crn-meta-validate">back to top</a>)</p>

<!-- LICENSE -->
## License
Distributed under the BSD-2-Clause license - see the `LICENSE` file for details.

<p align="right">(<a href="#crn-meta-validate">back to top</a>)</p>
