# crn-meta-validate
Metadata validator for ASAP CRN metadata (v0.5)

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
    <li><a href="#authors">Authors</a></li>
    <li><a href="#contact">Contact</a></li>
    <li><a href="#acknowledgments">Acknowledgments</a></li>
    <li><a href="#license">License</a></li>
  </ol>
</details>

<!-- ABOUT THE APP -->
## About the app

This app assists ASAP CRN data contributors to QC their metadata tables (e.g. STUDY.csv, SAMPLE.csv, PROTOCOL.csv, etc.) before uploading them to ASAP CRN Google buckets.    

We do this in three steps:    
**Step 1.** Set up your run, indicate type of dataset to determine expected tables and columns and upload your files.    
**Step 2.** The app will help to fix common issues, like non-comma delimiters and missing values.    
**Step 3.** The app reports missing columns and value mismatches vs. the [ASAP CRN Common Data Elements (CDE)](https://docs.google.com/spreadsheets/d/1c0z5KvRELdT2AtQAH2Dus8kwAyyLrR0CROhKOjpU4Vc/edit?).    

Two types of issues will be reported:    
* Errors: Must be fixed by the data contributors before uploading metadata to ASAP CRN Google buckets.    
* Warnings: Recommended to be fixed before uploading, but not required.    

<p align="right">(<a href="#crn-meta-validate">back to top</a>)</p>

<!-- GETTING STARTED / WEB APP -->
## How to use the web app

1. Go to the [web app](https://asap-meta-qc.streamlit.app/)    
2. Set up your run:   
    * In the drop-down menus, specify the following properties for your dataset: `Species`, `Tissue/Cell origin` and `Modality`    
    * A left-side menu will appear, showing the list if os expected `{TABLE}.csv` files for your dataset.   
    * You can Drag & drop, or  Browse your files to upload.
3. Files will be uploaded automatically and log messages will appear in the left-side menu.   
4. For each file, the app will look for non-comma delimiters and provide buttons to accept or reject the changes.
5. For each file, the app will look for with missing values and provide options to fill them out.
    * If changes were made, a preview of the filled out `{TABLE}` will be shown.
6. The `{TABLE}` without missing values will be compared vs the [ASAP CRN controlled vocabilaries (CDE)](https://docs.google.com/spreadsheets/d/1c0z5KvRELdT2AtQAH2Dus8kwAyyLrR0CROhKOjpU4Vc/edit?usp=sharing).
7. A report will be provided, including:
    * ✅ **Successful** steps    
    * ❌ **Errors** to be fixed by _data contributors_ before uploading sanitized files to ASAP Google Cloud buckets   
    * ⚠️ **Warnings** which the authors may opt to fix or not, depending on the dataset experiment configuration   
8. At the end, two files can be downloaded:
    * A `{TABLE}.md` markup file with the run report   
    * The `{TABLE}_after_cde_comparison.csv` file. Note: button will be enabled only if no errors were found.
9. Repeat steps 6 to 8 for each `{TABLE}.csv` file you uploaded.
10. Upload your final files to the Google bucket following [these instructions](https://docs.google.com/document/d/1Bicp20M0Zi_dc2-4nQJZwOCy5E20LJte0wT9pgKeVag/edit?usp=sharing)
11. Once you've completed uploading your metadata, raw data, and artifacts to the Google bucket, inform our [data manager](matthieu.darracq@dnastack.com). We will notify you if any issues are found.

**Notes:**    
a) If you have multiple datasets to validate, complete steps 2 to 11 for each dataset separately.     
b) The latest version of Common Data Elements (CDE i.e., ASAP CRN controlled vocabularies) will be used automatically.    
c) We are here to help. [Contact us](#contact) if you need a different version or have questions.    
d) Example *csv infiles can be downloaded from [here](https://github.com/ASAP-CRN/crn-meta-validate/tree/Update_Streamlit_NewModalties_and_UX/resource/tester_files
)

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

### Staging web app
Staging [web app URL](https://asap-crn-crn-meta-validate-app-update-streamlit-newmodal-m1gdf4.streamlit.app) from `Update_Streamlit_NewModalties_and_UX` branch

### Contributing
Contributions are what make the open source community such an amazing place to learn, inspire, and create. Any contributions you make are **greatly appreciated**. If you have a suggestion that would make this better, please do this and thanks again!
1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

<p align="right">(<a href="#crn-meta-validate">back to top</a>)</p>

<!-- AUTHORS -->
## Authors
- [Andy Henrie](https://github.com/ergonyc)
- [Javier Diaz](https://github.com/jdime)

<p align="right">(<a href="#crn-meta-validate">back to top</a>)</p>

<!-- CONTACT -->
## Contact
Please send us an email to [support@dnastack.com](support@dnastack.com) describing the issue, please include:   
* The {TABLE}.md file(s) that you get from the app (if you reached that point).
* Screenshots of the run setup and step where you got the issues(s).

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
