# crn-meta-validate
Metadata validator for ASAP CRN metadata (v0.9.2)

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
**Step 5. CDE validation:** the app reports missing columns and value mismatches vs. the [ASAP CRN controlled vocabularies (CDE) v4.2](https://docs.google.com/spreadsheets/d/1c0z5KvRELdT2AtQAH2Dus8kwAyyLrR0CROhKOjpU4Vc/edit?usp=sharing).

Two types of issues will be reported:     
**Errors (❌):**  must be fixed by the data contributors before uploading metadata to ASAP CRN Google buckets.     
**Warnings (⚠️):** recommended to be fixed before uploading, but not required.     

Free text boxes allow users to record per-column comments to provide context to data curators during review.

<!-- APP_INTRO_END -->

<p align="right">(<a href="#crn-meta-validate">back to top</a>)</p>

<!-- GETTING STARTED / WEB APP -->
## How to use the web app

👉 **[Open the app](https://asap-meta-qc.streamlit.app/)**

📖 **[Full step-by-step documentation](https://asap-crn.github.io/crn-meta-validate/)**

The documentation covers all five steps with screenshots, a FAQ, and download instructions.     
Example CSV files to test the app are available [here](https://github.com/ASAP-CRN/crn-meta-validate/tree/main/resource/tester_files).

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

3. Build a Python virtual environment including the requirements specified in `requirements.txt` 

4. Run the streamlit app locally
```bash
streamlit run app.py
```

5. Run the MkDocs locally
```bash
mkdocs serve
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
- [Javier Diaz](https://github.com/jdime)
- [Andy Henrie](https://github.com/ergonyc)

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
