import click
from loguru import logger
from pathlib import Path
from api_clients.inspire import InspireClient, LHCbPaper
from tqdm import tqdm
from dataclasses import dataclass
from typing import Optional, Sequence


@dataclass(frozen=True, slots=True)
class CorpusConfig:
    """Configuration for corpus building process."""

    start_date: Optional[str]
    end_date: Optional[str]
    max_papers: int
    download: bool
    output_dir: Path
    verbose: bool


class CorpusBuilder:
    """Class orchestrating the building an LHCb paper corpus from scraper API."""

    def __init__(self, config: CorpusConfig):
        self.config = config
        self._setup_logger()
        self.client = self._init_inspire_client()

    def _setup_logger(self):
        """Configure logger based on elected verbosity level."""
        log_level = "DEBUG" if self.config.verbose else "INFO"
        logger.remove()
        logger.add(
            "corpus_build.log",
            rotation="1 week",
            level=log_level,
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}",
        )
        logger.add(lambda msg: click.echo(msg, err=True), level=log_level)

    def _init_inspire_client(self) -> InspireClient:
        """Initialize INSPIRE client with configured directories."""

        return InspireClient(
            abstract_dir=self.config.output_dir / "abstracts",
            pdf_dir=self.config.output_dir / "pdfs",
            source_dir=self.config.output_dir / "source",
            expanded_tex_dir=self.config.output_dir / "expanded_tex",
        )

    def download_paper(self, paper: LHCbPaper) -> bool:
        """Download PDF and LaTeX source for a single paper.

        Parameters
        ----------
        paper: LHCbPaper
            Paper object to download, defined in scraping.inspire module

        Returns
            bool: True if either PDF or source was successfully downloaded
        """
        success = False

        if paper.arxiv_pdf:
            pdf_path = self.client.download_pdf(paper)
            if pdf_path:
                logger.debug(f"Downloaded PDF: {pdf_path}")
                success = True

        if paper.latex_source:
            source_path = self.client.download_paper_source(paper)
            if source_path:
                logger.debug(f"Downloaded and expanded source: {source_path}")
                success = True

        if paper.abstract:
            abstract_path = self.client.download_abstract(paper)

            if abstract_path:
                logger.debug(f"Downloaded abstract: {abstract_path}")
                success = True

        return success

    def build(self) -> None:
        """Enact the building of the corpus, downloading PDF and latexpanded TeX source."""
        logger.info(
            f"Starting corpus build: max_papers={self.config.max_papers}, "
            f"download={self.config.download}, output_dir={self.config.output_dir}"
        )
        papers: Sequence[LHCbPaper] = self.client.fetch_lhcb_papers(
            start_date=self.config.start_date,
            end_date=self.config.end_date,
            max_results=self.config.max_papers,
            sort_by="mostcited",
        )

        logger.info(f"Found {len(papers)} papers on INSPIRE")

        if not papers:
            logger.warning("No papers found matching the query criteria, exiting.")
            return

        # if requested, download PDF and source for each paper
        if self.config.download:
            failed_downloads = []
            for paper in tqdm(papers, desc="Downloading and unpacking LHCb papers"):
                logger.info(
                    f"Fetched LHCb paper '{paper.title}' (arXiv:{paper.arxiv_id}) [{paper.citations} citations to date]"
                )

                try:
                    success = self.download_paper(paper)
                    if not success:
                        failed_downloads.append(paper)
                        logger.warning(
                            f"Failed to download paper '{paper.title}' "
                            f"(arXiv:{paper.arxiv_id})"
                        )
                except Exception as e:
                    failed_downloads.append(paper)
                    logger.error(
                        f"Error downloading paper '{paper.title}' "
                        f"(arXiv:{paper.arxiv_id}): {str(e)}"
                    )

            logger.info(
                f"Successfully downloaded {len(papers) - len(failed_downloads)}/{len(papers)} papers"
            )

            if failed_downloads:
                failed_titles = [
                    f"'{p.title}' (arXiv:{p.arxiv_id})" for p in failed_downloads
                ]
                logger.warning(
                    f"Failed to download {len(failed_downloads)} papers:\n"
                    + "\n".join(f"- {title}" for title in failed_titles)
                )


def validate_date(
    ctx: click.Context, param: click.Parameter, value: Optional[str]
) -> Optional[str]:
    """
    Validate date format (YYYY-MM-DD).

    Parameters
    ----------
    ctx: click.Context
        Click context
    param: click.Parameter
        Click parameter
    value: Optional[str]
        Date string to validate

    Returns
    -------
    Optional[str]
        Date string if valid, None otherwise
    """
    if not value:
        return None

    try:
        year, month, day = value.split("-")
        assert len(year) == 4 and len(month) == 2 and len(day) == 2
        assert 1900 <= int(year) <= 2100
        assert 1 <= int(month) <= 12
        assert 1 <= int(day) <= 31
        return value
    except (ValueError, AssertionError):
        raise click.BadParameter("Date must be in YYYY-MM-DD format")


def validate_paper_count(
    ctx: click.Context, param: click.Parameter, value: Optional[int]
) -> Optional[int]:
    """
    Validate paper count is a positive integer.

    Parameters
    ----------
    ctx: click.Context
        Click context
    param: click.Parameter
        Click parameter
    value: Optional[int]
        Number of papers to download

    Returns
    -------
    Optional[int]
        Number of papers to download if positive
    """
    if value is not None and value <= 0:
        raise click.BadParameter("Number of papers must be positive")
    return value


@click.command()
@click.option(
    "--start-date",
    "-s",
    help="Start date for paper search (YYYY-MM-DD)",
    callback=validate_date,
)
@click.option(
    "--end-date",
    "-e",
    help="End date for paper search (YYYY-MM-DD)",
    callback=validate_date,
)
@click.option(
    "--max-papers",
    "-n",
    default=None,
    type=click.IntRange(1, 10_000),
    callback=validate_paper_count,
    help="Maximum number of papers to download (default: no limit)",
)
@click.option(
    "--download/--no-download",
    default=True,
    help="Download PDFs and LaTeX source for papers",
)
@click.option(
    "--output-dir",
    "-o",
    type=click.Path(path_type=Path),
    default=Path("data"),
    help="Base directory for downloaded files",
)
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose logging")
def main(**kwargs) -> None:
    """Build an LHCb paper corpus from INSPIRE-HEP.

    Fetches LHCb collaboration papers from INSPIRE-HEP and optionally downloads their
    PDFs and LaTeX sources. Papers can be filtered by date range and are stored in a
    structured directory layout.

    Downloads the following files for each paper (when available):
    - PDF document
    - LaTeX source files
    - Expanded LaTeX source (all includes resolved)
    - Paper abstract
    """
    if (
        kwargs.get("start_date")
        and kwargs.get("end_date")
        and kwargs["start_date"] > kwargs["end_date"]
    ):
        raise click.BadParameter("Start date must be before end date")

    config = CorpusConfig(**kwargs)
    builder = CorpusBuilder(config)
    builder.build()


if __name__ == "__main__":
    main()
