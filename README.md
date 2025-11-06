# crn-meta-validate
v3 metadata validator for ASAP CRN metadata

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

Welcome to the ASAP CRN metadata QC app. This app assists ASAP Team _data contributors_ to QC their metadata **`{TABLE}.csv` files** (incl. STUDY.csv, PROTOCOL.csv, SUBJECT.csv, etc.). The app will look for and fix common issues (e.g. fill out missing values with NA) and suggest changes that _data contributors_ need to address to align files to ASAP CRN standards.

If you have questions, please send us an email to [EMAIL](mailto:abc@def) describing the issue, include the *log.txt file(s) that you get from the app (see below) and a screenshot of the run setup.

<p align="right">(<a href="#crn-meta-validate">back to top</a>)</p>

<!-- GETTING STARTED / WEB APP -->
## How to use the web app

**Note:** If you have multiple datasets to validate, complete steps 1-9 for each dataset separately.

1. Go to the [web app](https://asap-meta-qc.streamlit.app/)
2. In the drop-down menus, specify the following for your dataset:
    * Species
    * Modality
    * Tissue/Cell origin
    * Common Data Elements version (CDE, i.e., ASAP CRN controlled vocabularies; the latest version is used by default)
3. A left-side menu will appear. Click `Browse files` and upload your `{TABLE}.csv` files
4. Files will be uploaded automatically, and global status messages will appear in the left-side menu
5. In the `Choose a TABLE to validate` drop-down menu, select the {TABLE} you want to validate
    * It will be processed automatically, and log messages will appear
6. Review the validation results:
    * **If issues are found**, two Download buttons will appear:
      * `Download your {TABLE}_log.txt`
        * **ERRORS**: are issues that _data contributors_ **must** fix before uploading files to ASAP Google Cloud buckets
        * **WARNINGS**: are issues that _data contributors_ **may optionally** address depending on the context
      * `Download a sanitized {TABLE}.csv`
        * An updated file with common issues fixed (e.g., missing values filled with NA)
    * **If no issues are found**, a `No issues found` message will appear
7. Repeat steps 5-6 for each {TABLE}.csv file you uploaded
8. Upload your final files to the Google bucket following [these instructions](https://docs.google.com/document/d/1Bicp20M0Zi_dc2-4nQJZwOCy5E20LJte0wT9pgKeVag/edit?usp=sharing)
9. Once you've completed uploading your metadata, raw data, and artifacts to the Google bucket, inform our [data manager](mailto:abc@def). We will notify you if any issues are found.

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
git clone git@github.com:ergonyc/asap_sc_collect.git 
```

2. Make sure you have access to some paths hard coded within the app not added on the github remote

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

<!-- AUTHORS -->
## Authors
- [Andy Henrie](https://github.com/ergonyc)
- [Javier Diaz](https://github.com/jdime)

<p align="right">(<a href="#crn-meta-validate">back to top</a>)</p>

<!-- CONTACT -->
## Contact
Please send us an email to [EMAIL](mailto:abc@def) describing the issue, include the *log.txt file(s) that you get from the app (see below) and a screenshot of the run setup.

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
