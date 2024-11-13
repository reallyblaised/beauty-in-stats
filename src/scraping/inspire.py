from pydantic import BaseModel

class InspirePaperMetadata(BaseModel):
    """Metadata for a paper on INSPIRE-HEP."""
    title: str
    authors: list[str]
    citation_count: int
    arxiv_id: Optional[str] = None
    arxiv_pdf: Optional[str] = None
    cds_id: Optional[str] = None
    date: Optional[dict] = None
    document_type: Optional[str] = None
    authors: Optional[list[str]] = None
    doi: Optional[str] = None

class InspireClient: 
    """Client for interacting with the INSPIRE-HEP API."""

    def __init__(self) -> None:
        self.base_url = settings.INSPIRE_API_URL
