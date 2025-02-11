# Build the LHCb Paper Corpus

Apt data curation is critical to the development of the LHCb analysis copilot. Therefore, development starts with retrieving from the LHCb paper archive the metadata of all papers, focusing on the `Working Group` and `Years/Run` fields; the paper LHCb and arXiv identifiers; and the raw abstracts in LaTeX format.

A codebase-to-become-an-agent has been developed to scrape the LHCb paper archive and extract the metadata. This README provides instructions for running the scraper using Docker or Apptainer.

The SubMIT node with GPU access does not have a browser. To scrape the LHCb paper archive, a headless browser is used, installing it a dedicated container to avoid conflicts with the SubMIT system.

The scraper can be run using Docker or Apptainer. This README provides instructions for both setups, with a preference for using Apptainer to inherit GPU access from the host.


## Prerequisites

- **Apptainer**: Ensure Apptainer is installed. You can find installation instructions [here](https://apptainer.org/docs/user/quickstart.html).
- **NVIDIA GPU**: If you want to use GPU acceleration, ensure you have an NVIDIA GPU and the necessary drivers installed.
- **Docker** [Optional]: Ensure Docker is installed and running on your machine.

## Using Apptainer [preferred on SubMIT]

1. **Build the Apptainer Image**:
   Navigate to the directory `src/scraper/containers` and run the following command:

   ```bash
   apptainer build containers/lhcb-scraper-container.sif containers/Apptainer.def
   ```

   If you are using GPU acceleration, you can verify that the GPU is accessible within the Apptainer container by running:

   ```bash
   apptainer exec --nv containers/lhcb-scraper-container.sif nvidia-smi
   ```

   This command should display the GPU information if the setup is correct.


2. **Run the Apptainer Container with GPU Access**:
   To run the scraper with GPU access, use the following command:

   ```bash
   apptainer shell --nv containers/lhcb-scraper-container.sif
   ```

   The `--nv` flag allows the container to access the GPU resources of the host.

3. **Run the Scraper**:
   Navigate to the directory `src/scraper` and run the following command:

   ```bash
   python scripts/scrape_build_lhcb_papers.py [--max-papers N] [--download] [--output-dir DIR]
   ```

   This script will scrape the LHCb paper archive and save the metadata to a CSV and pickle files. Additionally, if the `--download` flag is set to True, the script will download the papers and save them to the `data/pdfs` and `data/source` directories. Expansion (i.e. generating a monolithic `<arxiv_id>.tex` expanding all imports) and boilerplate removal of the TeX source is also performed if the `--download` flag is set to True, saving the expanded and processed TeX source to the `data/expanded` and `data/boilerplate_free_tex` directories, respectively.

   **Flags**:

   The `--max_papers N` flag allows you to specify the maximum number of papers to scrape. The `--download` flag allows you to download the papers. The `--output_dir DIR` flag allows you to specify the output directory.

   The default values are:
   - `--max_papers`: `None`
   - `--download`: `True`
   - `--output_dir`: `data`

4. **Inspect the data**:
   Navigate to the directory `data` and inspect the files. Note that the `source` directory contains the raw TeX source files, which are not cleaned of boilerplate. The summary dataframe is saved in `data/summary.pkl`, containing the metadata and abstract of all papers.

5. **Cleanup after yourself**:
   When you are done, you can exit the container by running the following command:

   ```bash
   exit # exit the container
   apptainer cache clean  # clean the cache
   rm containers/lhcb-scraper-container.sif # remove the container
   ```

6. **Debugging**:
   If you encounter any issues, you can debug the container by running the following command (with the container not running):

   ```bash
   apptainer exec -B $(pwd):/opt/lhcb-project containers/lhcb-scraper-container.sif \
    bash -c "PYTHONPATH=/opt/lhcb-project PYTHONDONTWRITEBYTECODE=1 python /opt/lhcb-project/scripts/scrape_build_lhcb_papers.py -n 1"
   ```

   This will execute the `scrape_build_lhcb_papers.py` script inside the container, allowing you to modify relative imports and run the `/opt/lhcb-project/scripts/scrape_build_lhcb_papers.py` primary script. Notice how, for convenience, here only one paper is scraped.

## Using Docker [Experimental, not recommended]

1. **Build the Docker Image** [Experimental, not recommended]:
   Navigate to the directory `src/scraper/containers` and run the following command:

   ```bash
   docker build -t lhcb_scraper .
   ```

   This will build the Docker image and tag it as `lhcb_scraper`.

2. **Run the Docker Container**:
   Navigate to the directory `src/scraper/scripts` and run the following command:

   ```bash
   docker run --rm lhcb_scraper
   ```

