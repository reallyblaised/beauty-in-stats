from typing import Optional, List, Dict
from pathlib import Path
import requests
from pydantic import BaseModel
from loguru import logger

class LHCbPaper(BaseModel):
    """Basic paper metadata"""
    title: str
    citations: int = 0
    arxiv_id: Optional[str] = None
    arxiv_pdf: Optional[str] = None
    latex_source: Optional[str] = None

class InspireClient:
    """Minimal client for INSPIRE-HEP API."""
    
    def __init__(self, pdf_dir: Path, source_dir: Path):
        self.base_url = "https://inspirehep.net/api"
        self.pdf_dir = pdf_dir # pdf of the paper
        self.source_dir = source_dir # latex source of the paper
        self.pdf_dir.mkdir(parents=True, exist_ok=True)
        self.source_dir.mkdir(parents=True, exist_ok=True)

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
            breakpoint()

            # Extract arXiv ID if available
            arxiv_id = None
            if 'arxiv_eprints' in metadata and metadata['arxiv_eprints']:
                arxiv_id = metadata['arxiv_eprints'][0].get('value')
            
            # Create paper object
            paper = LHCbPaper(
                title=metadata['titles'][0]['title'],
                citations=metadata.get('citation_count', 0),
                arxiv_id=arxiv_id,
                arxiv_pdf=f"https://arxiv.org/pdf/{arxiv_id}.pdf" if arxiv_id else None,
                latex_source=f"https://arxiv.org/e-print/{arxiv_id}" if arxiv_id else None
            )
            papers.append(paper)
            
        return papers

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

    def download_source(self, paper: LHCbPaper) -> Optional[Path]:
        """Download LaTeX source if available."""
        if not paper.latex_source:
            return None
            
        try:
            response = requests.get(paper.latex_source)
            response.raise_for_status()
            
            # Simply use arxiv_id as filename
            filepath = self.source_dir / f"{paper.arxiv_id}_source.tar.gz"
            filepath.write_bytes(response.content)
            return filepath
            
        except requests.RequestException as e:
            logger.error(f"Failed to download source: {e}")
            return None