from typing import List, Optional
from pydantic import BaseModel, Field

class LHCbPaper(BaseModel):
    """Model representing an LHCb paper with its metadata."""
    lhcb_paper_id: str = Field(..., description="Unique identifier for the paper")
    title: str = Field(..., description="Paper title")
    arxiv_id: str = Field(None, description="arXiv identifier if available")
    citations: int = Field(0, description="Number of citations")
    working_groups: List[str] = Field(default_factory=list, description="Associated working groups")
    data_taking_years: List[str] = Field(default_factory=list, description="Data-taking years")
    run_period: str = Field(..., description="Run period")
    abstract: str = Field(..., description="Paper abstract")
    latex_source: Optional[str] = Field(None, description="LaTeX source code")
    pdf_url: Optional[str] = Field(None, description="PDF URL")
    arxiv_pdf: Optional[str] = Field(None, description="arXiv PDF URL")
    
    