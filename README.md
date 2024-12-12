<img src="./assets/beauty-in-stats-logo.png" alt="BeautyInStats Logo" width="1000"/>

# BeautyInStats
An explainable agentic workflow as analysis copilot for LHCb OpenData and dissemination of best-practice methods for the apt evaluation of systematic uncertainties.  

# Development Guide

## Setup

1. Prerequisites

```bash
python3 -m pip install --user pipx
python3 -m pipx ensurepath
source ~/.bashrc # or any other default shell
```

2. Install [Poetry](https://python-poetry.org) (package manager):

```bash
pipx install poetry
```

3. Clone the repository and install dependencies

```bash
git clone https://github.com/reallyblaised/beauty-in-stats.git
cd beauty-in-stats
poetry install
```

4. Verify the correct installation of the Poetry environment 

```bash
poetry env list
>>> beautyinstats-U3Bi8mYg-py3.10 (Activated)
```

5. Load the Poetry shell to load the library environment
```bash
 poetry shell
 ```

## Build the LHCb paper corpus

```bash
# Get all papers
build-corpus

# Get specific number of papers
build-corpus --max-papers 10

# Get papers from date range
build-corpus --start-date 2020-01-01 --end-date 2023-12-31

# Show additional logging
build-corpus --verbose
```

Downloaded files are organized in the `data/` directory:

```bash
data/pdfs/: PDF versions of papers
data/source/: LaTeX source files
data/expanded_tex/: Expanded LaTeX files
data/abstracts/: Paper abstracts
```

## Dependencies

- Python ≥ 3.9
- `latexpand` (for processing LaTeX sources)