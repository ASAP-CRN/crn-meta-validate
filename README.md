# crn-meta-validate
v2 metadata validator for ASAP CRN metadata

<a name="readme-top"></a>

<!-- PROJECT SHIELDS -->
<!--
*** I'm using markdown "reference style" links for readability.
*** Reference links are enclosed in brackets [ ] instead of parentheses ( ).
*** See the bottom of this document for the declaration of the reference variables
*** for contributors-url, forks-url, etc. This is an optional, concise syntax you may use.
*** https://www.markdownguide.org/basic-syntax/#reference-style-links
-->

<!-- PROJECT LOGO -->
<br />
<div align="center">

  <h3 align="center">ASAP CRN Cloud Platform metadata QC app</h3>

  <p align="center">
    An app that allows you to QC your metadata
    <br />
    <br />
  </p>
</div>



<!-- TABLE OF CONTENTS -->
<details>
  <summary>Table of Contents</summary>
  <ol>
    <li>
      <a href="#about-the-app">About the app</a>
    </li>
    <li>
      <a href="#getting-started">Getting Started</a>
      <ul>
        <li><a href="#prerequisites">Prerequisites</a></li>
        <li><a href="#installation">Installation</a></li>
      </ul>
    </li>
    <li><a href="#usage">Usage</a></li>
    <li><a href="#contact">Contact</a></li>
    <li><a href="#acknowledgments">Acknowledgments</a></li>
  </ol>
</details>


<!-- ABOUT THE PROJECT -->
## About the app

Welcome to the ASAP CRN metadata QC app. This is an application intended to make easier the burden of harmonizing the data to ASAP CRN standards. 

In the future this may also  assign ASAP CRN IDs.


The intended workflow is as follow:
* upload csvs to to the app ( clinical tab)

<p align="right">(<a href="#readme-top">back to top</a>)</p>




<p align="right">(<a href="#readme-top">back to top</a>)</p>


<!-- GETTING STARTED -->
## Getting Started

Try it out deployed via [streamlit] (https://asap-meta-qc.streamlit.app/)

### Prerequisites

* Docker installed
* Python3.11 higher


### Installation 

If you wanted to run this app locally and play with it, it should be as simple as:

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


<p align="right">(<a href="#readme-top">back to top</a>)</p>



<!-- USAGE EXAMPLES -->
## Usage

Load your metadata tables, and generate a report

<p align="right">(<a href="#readme-top">back to top</a>)</p>



<!-- CONTRIBUTING -->
## Contributing

Contributions are what make the open source community such an amazing place to learn, inspire, and create. Any contributions you make are **greatly appreciated**.

If you have a suggestion that would make this better, please fork the repo and create a pull request.
Thanks again!

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

<p align="right">(<a href="#readme-top">back to top</a>)</p>



<!-- LICENSE -->
## License

Distributed under the MIT License. See `LICENSE.txt` for more information.

<p align="right">(<a href="#readme-top">back to top</a>)</p>



<!-- CONTACT -->
## Contact

Also email me on henrie@datatecnica.com

Project Link: [TBD]

<p align="right">(<a href="#readme-top">back to top</a>)</p>



<!-- ACKNOWLEDGMENTS -->
## Acknowledgments

This would not be possible without help of the Data Tecnica team, specially Alejandro Martinez, and the similar GP2 tool 
* [DtI](https://www.datatecnica.com/)
* [ASAP CRN]

<p align="right">(<a href="#readme-top">back to top</a>)</p>



<!-- MARKDOWN LINKS & IMAGES -->
<!-- https://www.markdownguide.org/basic-syntax/#reference-style-links -->
[do-shield]: https://img.shields.io/badge/docker-%230db7ed.svg?style=for-the-badge&logo=docker&logoColor=white
[do-url]: https://www.docker.com/
[st-shield]: https://user-images.githubusercontent.com/7164864/217935870-c0bc60a3-6fc0-4047-b011-7b4c59488c91.png
[st-url]: https://streamlit.io/
[py-shield]: https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54
[python-url]: https://www.python.org/
[gcp-url]: https://cloud.google.com/?hl=en
