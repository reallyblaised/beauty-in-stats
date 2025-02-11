from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings and paths."""

    # project structure
    BASE_DIR: Path = Path(__file__).resolve().parent.parent
    DATA_DIR: Path = BASE_DIR / "data"
    PDF_DIR: Path = DATA_DIR / "pdfs"
    PROCESSED_DIR: Path = DATA_DIR / "processed"

    # APIs used to fetch manuscripts and metadata
    INSPIRE_API_URL: str = "https://inspirehep.net/api"

    # setup directory structure
    def setup_directories(self):
        """Create necessary directories, if absent."""
        for dir in [self.DATA_DIR, self.PDF_DIR, self.PROCESSED_DIR]:
            dir.mkdir(parents=True, exist_ok=True)


# instantiate settings
settings = Settings()
