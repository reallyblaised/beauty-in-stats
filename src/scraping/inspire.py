from typing import Optional, List, Dict
from pathlib import Path
import requests, tarfile
from pydantic import BaseModel, ConfigDict
from loguru import logger
import subprocess
import os


class LHCbPaper(BaseModel):
    """LHCb paper metadata"""
    model_config = ConfigDict(frozen=True) # immutable post-creation

    # fields
    title: str
    citations: int = 0
    arxiv_id: Optional[str] = None
    abstract: Optional[str] = None
    arxiv_pdf: Optional[str] = None
    latex_source: Optional[str] = None


class InspireClient:
    """Minimal client for INSPIRE-HEP API."""
    
    def __init__(
        self, 
        abstract_dir: Path,
        pdf_dir: Path, 
        source_dir: Path, 
        expanded_tex_dir: Path
    ):
        self.base_url = "https://inspirehep.net/api"
        self.abstract_dir = abstract_dir # arxiv abstract
        self.pdf_dir = pdf_dir # pdf of the paper
        self.source_dir = source_dir # latex source of the paper, with all source files
        self.expanded_tex_dir = expanded_tex_dir # expanded latex source of the paper
        self.pdf_dir.mkdir(parents=True, exist_ok=True)
        self.source_dir.mkdir(parents=True, exist_ok=True)
        self.expanded_tex_dir.mkdir(parents=True, exist_ok=True)

    def fetch_papers(self, max_results: int = 10) -> List[LHCbPaper]:
        """Fetch LHCb papers, sorted by citation count."""
        params = {
            'q': 'collaboration:"LHCb" and document_type:article',  
            'sort': 'mostcited',   
            'size': max_results,
            'fields': [
                "titles,arxiv_eprints,dois,citation_count,abstracts,"
                ]
        }
        
        response = requests.get(f"{self.base_url}/literature", params=params)
        response.raise_for_status()

        papers = []
        for hit in response.json()['hits']['hits']:
            metadata = hit['metadata']

            # Extract arXiv ID if available
            arxiv_id = None
            if 'arxiv_eprints' in metadata and metadata['arxiv_eprints']:
                arxiv_id = metadata['arxiv_eprints'][0].get('value')
            
            # Create paper object
            paper = LHCbPaper(
                title=metadata['titles'][0]['title'],
                citations=metadata.get('citation_count', 0),
                arxiv_id=arxiv_id,
                abstract=metadata.get('abstracts', [{}])[1].get('value'),
                arxiv_pdf=f"https://arxiv.org/pdf/{arxiv_id}.pdf" if arxiv_id else None,
                latex_source=f"https://arxiv.org/e-print/{arxiv_id}" if arxiv_id else None
            )
            papers.append(paper)

        return papers

    def download_abstract(self, paper: LHCbPaper) -> Optional[Path]:
        """Download the arxiv abstract, if available, with latex notation."""
        if not paper.abstract:
            return None
            
        try:
            response = requests.get(paper.abstract)
            response.raise_for_status()
            
            # Simply use arxiv_id as filename
            filepath = self.abstract_dir / f"{paper.arxiv_id}.txt"
            filepath.write_text(response.text)
            return filepath
            
        except requests.RequestException as e:
            logger.error(f"Failed to download abstract: {e}")
            return None

    def download_pdf(self, paper: LHCbPaper) -> Optional[Path]:
        """Download PDF if available."""
        if not paper.arxiv_pdf:
            return None
            
        try:
            response = requests.get(paper.arxiv_pdf)
            response.raise_for_status()
            
            # Simply use arxiv_id as filename
            filepath = self.pdf_dir / f"{paper.arxiv_id}.pdf"
            filepath.write_bytes(response.content)
            return filepath
            
        except requests.RequestException as e:
            logger.error(f"Failed to download PDF: {e}")
            return None

    def find_main_tex(self, directory: Path) -> Optional[Path]:
        """Find the main TeX file in a directory."""
        tex_files = list(directory.glob("*.tex"))
        
        # Common main file names
        main_candidates = ["main.tex", "paper.tex", "article.tex"]
        
        # First try common names
        for candidate in main_candidates:
            main_file = directory / candidate
            if main_file in tex_files:
                return main_file
        
        # If no common names found, look for .tex files that might contain documentclass
        for tex_file in tex_files:
            content = tex_file.read_text(errors='ignore')
            if r'\documentclass' in content:
                return tex_file
                
        return None

    def extract_and_expand_latex(self, paper: LHCbPaper, source_file: Path) -> Optional[Path]:
        """Extract LaTeX source and expand the main file."""
        if not source_file.exists():
            logger.error(f"Source file not found: {source_file}")
            return None
            
        # Create a unique directory for this paper
        paper_dir = self.source_dir / f"{paper.arxiv_id}"
        paper_dir.mkdir(exist_ok=True)
        
        # Extract the tar.gz file
        try:
            with tarfile.open(source_file, 'r:gz') as tar:
                tar.extractall(path=paper_dir)
            
            # upon successful extraction, remove the tar.gz file
            source_file.unlink()
        except tarfile.ReadError as e:
            logger.error(f"Failed to extract source: {e}")
            return None

        # Find the main TeX file, where all imports are resolved
        main_tex = self.find_main_tex(paper_dir)
        if not main_tex:
            logger.error(f"Could not find main TeX file for {paper.arxiv_id}")
            return None
        
        # Create output path for expanded tex
        expanded_tex = self.expanded_tex_dir / f"{paper.arxiv_id}.tex"

        # book current working directory
        cwd = Path.cwd()

        # Run latexpand
        try:
            os.chdir(main_tex.parent) # latexpand needs to be run in the same directory as the main tex file
            result = subprocess.run(
                ['latexpand', str(main_tex)],
                capture_output=True,
                text=True,
                check=True
            )
            expanded_tex.write_text(result.stdout)

            # return to original working directory
            os.chdir(cwd)

            return expanded_tex
            
        except subprocess.CalledProcessError as e:
            logger.error(f"latexpand failed: {e}")
            return None
                
        except Exception as e:
            logger.error(f"Failed to process LaTeX source: {e}")
            return None
        
        
    def download_source(self, paper: LHCbPaper) -> Optional[Path]:
        """Download and process LaTeX source if available."""
        if not paper.latex_source:
            return None
            
        try:
            response = requests.get(paper.latex_source)
            response.raise_for_status()
            
            # Download the source
            source_file = self.source_dir / f"{paper.arxiv_id}_source.tar.gz"
            source_file.write_bytes(response.content)
            
            # Extract and expand the LaTeX
            expanded_file = self.extract_and_expand_latex(paper, source_file)
            return expanded_file
            
        except requests.RequestException as e:
            logger.error(f"Failed to download source: {e}")
            return None