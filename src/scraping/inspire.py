from typing import Optional, List, Dict, Any
from pathlib import Path
import requests
import tarfile
from pydantic import BaseModel, ConfigDict
from loguru import logger
import subprocess
import os
from tqdm import tqdm

class LHCbPaper(BaseModel):
    """Represents a scientific paper from the LHCb collaboration.

    Parameters
    ------------
    title : str
        Title of the paper
    citations : int, default=0
        Number of citations the paper has received
    arxiv_id : str, optional
        The arXiv identifier of the paper
    abstract : str, optional
        Paper abstract text
    arxiv_pdf : str, optional
        URL to the paper's PDF on arXiv
    latex_source : str, optional
        URL to the paper's LaTeX source on arXiv
    """

    model_config = ConfigDict(frozen=True)

    title: str
    citations: int = 0
    arxiv_id: Optional[str] = None
    abstract: Optional[str] = None
    arxiv_pdf: Optional[str] = None
    latex_source: Optional[str] = None


class InspireClient:
    """Client for interacting with the INSPIRE-HEP API."""

    def __init__(
        self,
        abstract_dir: Path = Path("data/abstracts"),
        pdf_dir: Path = Path("data/pdfs"),
        source_dir: Path = Path("data/source"),
        expanded_tex_dir: Path = Path("data/expanded_tex"),
    ) -> None:
        """Initialize the INSPIRE-HEP client.

        Parameters
        ------------
        abstract_dir : Path, default=Path("data/abstracts")
            Directory for storing paper abstracts
        pdf_dir : Path, default=Path("data/pdfs")
            Directory for storing PDF versions
        source_dir : Path, default=Path("data/source")
            Directory for storing LaTeX source files
        expanded_tex_dir : Path, default=Path("data/expanded_tex")
            Directory for storing expanded LaTeX files
        """
        self.base_url = "https://inspirehep.net/api"
        self.abstract_dir = abstract_dir
        self.pdf_dir = pdf_dir
        self.source_dir = source_dir
        self.expanded_tex_dir = expanded_tex_dir

        for directory in [
            self.abstract_dir,
            self.pdf_dir,
            self.source_dir,
            self.expanded_tex_dir,
        ]:
            directory.mkdir(parents=True, exist_ok=True)

    def __enter__(self) -> "InspireClient":
        """Context manager entry point.

        Returns
        ------------
        InspireClient
            The client instance
        """
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit point."""
        pass

    @staticmethod
    def get_arxiv_abstract(abstracts_list: List[Dict[str, Any]]) -> Optional[str]:
        """Extract arXiv abstract if available, otherwise take the first available abstract.

        Parameters
        ----------
        abstracts_list : List[Dict[str, Any]]
            List of abstract dictionaries from INSPIRE API

        Returns
        -------
        Optional[str]
            Abstract text if found, None otherwise
        """
        if not abstracts_list:
            return None

        # Try to find arXiv abstract first
        for abstract in abstracts_list:
            if abstract.get("source") == "arXiv":
                return abstract.get("value")

        # If no arXiv abstract, take the first available one
        return abstracts_list[0].get("value")

    def _fetch_papers(self, params: dict) -> List[LHCbPaper]:
        """Internal method to handle API requests and paper object creation.
        Handles pagination to fetch all results when no size limit is specified.
        """
        # Copy params so we don't modify the original
        params = params.copy()
        
        # Make initial request to get total number of papers
        response = requests.get(f"{self.base_url}/literature", params=params)
        response.raise_for_status()
        data = response.json()
        
        total_hits = data['hits']['total']
        logger.info(f"Total papers available: {total_hits}")
        
        if 'size' not in params:
            # No limit specified - fetch all papers
            params['size'] = 250  # API maximum per request
            papers = []
            
            for page in tqdm(range(1, (total_hits // 250) + 2), desc="Fetching LHCb papers from INSPIRE API"):
                params['page'] = page
                response = requests.get(f"{self.base_url}/literature", params=params)
                response.raise_for_status()
                
                for hit in response.json()['hits']['hits']:
                    metadata = hit['metadata']
                    arxiv_id = None
                    if 'arxiv_eprints' in metadata and metadata['arxiv_eprints']:
                        arxiv_id = metadata['arxiv_eprints'][0].get('value')
                    
                    paper = LHCbPaper(
                        title=metadata['titles'][0]['title'],
                        citations=metadata.get('citation_count', 0),
                        arxiv_id=arxiv_id,
                        abstract=self.get_arxiv_abstract(metadata.get('abstracts', [])),
                        arxiv_pdf=f"https://arxiv.org/pdf/{arxiv_id}.pdf" if arxiv_id else None,
                        latex_source=f"https://arxiv.org/e-print/{arxiv_id}" if arxiv_id else None
                    )
                    papers.append(paper)
                
                if len(response.json()['hits']['hits']) < 250:
                    break
        
        else:
            # Size limit specified - fetch single page
            papers = [
                LHCbPaper(
                    title=hit['metadata']['titles'][0]['title'],
                    citations=hit['metadata'].get('citation_count', 0),
                    arxiv_id=hit['metadata']['arxiv_eprints'][0].get('value') if 'arxiv_eprints' in hit['metadata'] and hit['metadata']['arxiv_eprints'] else None,
                    abstract=self.get_arxiv_abstract(hit['metadata'].get('abstracts', [])),
                    arxiv_pdf=f"https://arxiv.org/pdf/{arxiv_id}.pdf" if arxiv_id else None,
                    latex_source=f"https://arxiv.org/e-print/{arxiv_id}" if arxiv_id else None
                )
                for hit in data['hits']['hits']
            ]
        
        logger.info(f"Fetching COMPLETE: identified {len(papers)} papers on INSPIRE in TOTAL")
        return papers

    def fetch_lhcb_papers(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        max_results: Optional[int] = None,
        sort_by: str = "mostcited",
    ) -> List[LHCbPaper]:
        """Fetch LHCb collaboration papers from INSPIRE-HEP API.

        Parameters
        ------------
        start_date : str, optional
            Start date in YYYY-MM-DD format
        end_date : str, optional
            End date in YYYY-MM-DD format
        max_results : Optional[int], default=None
            Maximum number of papers to retrieve
        sort_by : str, default='mostcited'
            Sorting method for results ('mostcited', 'mostrecent')

        Returns
        ------------
        List[LHCbPaper]
            List of paper objects matching the search criteria
        """
        query = 'collaboration:"LHCb" and document_type:article'
        if start_date:
            query += f" and date>={start_date}"
        if end_date:
            query += f" and date<={end_date}"

        params = {
            "q": query,
            "sort": sort_by,
            "fields": ["titles,arxiv_eprints,dois,citation_count,abstracts"],
        }

        # if explicit limit is set on number of papers, cap the fetched results
        if max_results is not None:
            params["size"] = max_results

        return self._fetch_papers(params)

    def download_abstract(self, paper: LHCbPaper) -> Optional[Path]:
        """Save paper abstract to file if available.

        Parameters
        ------------
        paper : LHCbPaper
            Paper object containing the abstract text

        Returns
        ------------
        Optional[Path]
            Path to the saved abstract file, or None if abstract not available
        """
        if not paper.abstract:
            return None

        try:
            filepath = self.abstract_dir / f"{paper.arxiv_id}.tex"
            filepath.write_text(paper.abstract)
            return filepath

        except Exception as e:
            logger.error(f"Failed to save abstract: {e}")
            return None

    def download_pdf(self, paper: LHCbPaper) -> Optional[Path]:
        """Download PDF version if available.

        Parameters
        ------------
        paper : LHCbPaper
            Paper object containing the PDF URL

        Returns
        ------------
        Optional[Path]
            Path to the downloaded PDF file, or None if download failed
        """
        if not paper.arxiv_pdf:
            return None

        try:
            response = requests.get(paper.arxiv_pdf)
            response.raise_for_status()

            filepath = self.pdf_dir / f"{paper.arxiv_id}.pdf"
            filepath.write_bytes(response.content)
            return filepath

        except requests.RequestException as e:
            logger.error(f"Failed to download PDF: {e}")
            return None

    def find_main_tex(self, directory: Path) -> Optional[Path]:
        """Find the main TeX file in a directory.

        Parameters
        ------------
        directory : Path
            Directory containing TeX files

        Returns
        ------------
        Optional[Path]
            Path to the main TeX file, or None if not found
        """
        tex_files = list(directory.glob("*.tex"))

        main_candidates = ["main.tex", "paper.tex", "article.tex"]
        for candidate in main_candidates:
            main_file = directory / candidate
            if main_file in tex_files:
                return main_file

        for tex_file in tex_files:
            content = tex_file.read_text(errors="ignore")
            if r"\documentclass" in content:
                return tex_file

        return None

    def extract_and_expand_latex(
        self, paper: LHCbPaper, source_file: Path
    ) -> Optional[Path]:
        """Extract and expand LaTeX source into a single file.

        Parameters
        ------------
        paper : LHCbPaper
            Paper object to process
        source_file : Path
            Path to the downloaded source tarball

        Returns
        ------------
        Optional[Path]
            Path to the expanded LaTeX file, or None if processing failed
        """
        if not source_file.exists():
            logger.error(f"Source file not found: {source_file}")
            return None

        paper_dir = self.source_dir / f"{paper.arxiv_id}"
        paper_dir.mkdir(exist_ok=True)

        try:
            with tarfile.open(source_file, "r:gz") as tar:
                tar.extractall(path=paper_dir)

            source_file.unlink(missing_ok=True)
        except tarfile.ReadError as e:
            logger.error(f"Failed to extract source: {e}")
            return None

        main_tex = self.find_main_tex(paper_dir)
        if not main_tex:
            logger.error(f"Could not find main TeX file for {paper.arxiv_id}")
            return None

        # book the full path of the expanded directory to avoid conflicts whence cd to the source .tex directory
        expanded_tex = (self.expanded_tex_dir / f"{paper.arxiv_id}.tex").resolve()

        # bookeeping: save the current working directory before stepping into the .tex source directory
        cwd = Path.cwd()
        try:
            os.chdir(main_tex.parent)
            result = subprocess.run(
                ["latexpand", main_tex.name], capture_output=True, text=True, check=True
            )
            expanded_tex.write_text(result.stdout)
            return expanded_tex

        except subprocess.CalledProcessError as e:
            logger.error(f"latexpand failed: {e}")
            return None

        except Exception as e:
            logger.error(f"Failed to process LaTeX source: {e}")
            return None

        finally:
            os.chdir(cwd)

    def download_paper_source(self, paper: LHCbPaper) -> Optional[Path]:
        """Download and process paper source files.

        Parameters
        ------------
        paper : LHCbPaper
            Paper object containing the source URL

        Returns
        ------------
        Optional[Path]
            Path to the expanded LaTeX file, or None if processing failed
        """
        return self.download_source(paper)

    def download_source(self, paper: LHCbPaper) -> Optional[Path]:
        """Download and process paper source files.

        Parameters
        ------------
        paper : LHCbPaper
            Paper object containing the source URL

        Returns
        ------------
        Optional[Path]
            Path to the expanded LaTeX file, or None if processing failed
        """
        if not paper.latex_source:
            return None

        try:
            response = requests.get(paper.latex_source)
            response.raise_for_status()

            source_file = self.source_dir / f"{paper.arxiv_id}_source.tar.gz"
            source_file.write_bytes(response.content)

            expanded_file = self.extract_and_expand_latex(paper, source_file)
            return expanded_file

        except requests.RequestException as e:
            logger.error(f"Failed to download source: {e}")
            return None
