import click
from loguru import logger
from scraping.inspire import InspireClient
from tqdm import tqdm 

@click.command()
@click.option('--start-date', '-s', help='Start date in YYYY-MM-DD format')
@click.option('--end-date', '-e', help='End date in YYYY-MM-DD format')  # Added end date
@click.option('--max-papers', '-n', default=10, help='Maximum number of papers to fetch')
@click.option('--download/--no-download', default=True, help='Whether to download PDFs and sources')
def build_corpus(start_date: str, end_date: str, max_papers: int, download: bool):
    """Build the LHCb paper corpus from INSPIRE-HEP."""
    logger.info(f"Starting corpus build: max_papers={max_papers}, download={download}")
    
    with InspireClient() as client:
        papers = client.fetch_lhcb_papers(
            start_date=start_date,
            end_date=end_date,  
            max_results=max_papers,
            sort_by='mostcited'  
        )
        logger.info(f"Found {len(papers)} papers")
        
        if download and papers:
            for paper in tqdm(papers, desc="Downloading papers"):
                breakpoint()
                if paper.arxiv_pdf:
                    client.download_pdf(paper)
                if paper.latex_source:
                    client.download_paper_source(paper)

if __name__ == '__main__':
    build_corpus()