from pathlib import Path
from typing import List, Optional
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from time import sleep
import pandas as pd
from datetime import datetime
import argparse
import re
from loguru import logger
from api_clients.inspire import InspireClient
from core.models import LHCbPaper
from .build_lhcb_corpus import CorpusBuilder, CorpusConfig
from tqdm import tqdm

def normalize_working_group(wg: str) -> str:
    """Convert working group label to snake_case format"""
    wg = wg.strip().lower()
    wg = re.sub(r'[^a-z0-9]+', '_', wg)
    wg = wg.strip('_')
    return wg

def parse_working_groups(wg_cell: str) -> List[str]:
    """Parse and normalize multiple working groups from a cell"""
    working_groups = [wg.strip() for wg in wg_cell.split('\n') if wg.strip()]
    return [normalize_working_group(wg) for wg in working_groups]

def determine_run_period(years: List[str]) -> str:
    """Map years to LHC run periods"""
    if not years:
        return "unknown"
    
    run_periods = []
    for year in years:
        year = int(year)
        if year in {2011, 2012}:
            run_periods.append("Run1")
        elif year in {2015, 2016, 2017, 2018}:
            run_periods.append("Run2")
        elif year in {2023, 2024, 2025}:
            run_periods.append("Run3")
        else:
            run_periods.append("unknown")
    
    unique_periods = sorted(set(run_periods))
    return "+".join(unique_periods) if unique_periods else "unknown"

def parse_years(years_cells: str) -> List[str]:
    """Parse years from cell content"""
    if not years_cells.strip():
        return []
    return [year.strip() for year in years_cells.split() if year.strip().isdigit()]

def process_page(driver) -> List[dict]:
    """Process a single page of papers"""
    page_papers = []
    rows = driver.find_elements(By.TAG_NAME, "tr")
    
    for row in rows:
        cells = row.find_elements(By.TAG_NAME, "td")
        if len(cells) >= 8:
            try:
                title = cells[2].text.strip()
                arxiv_id = cells[4].text.strip()
                years = parse_years(cells[7].text)
                working_groups = parse_working_groups(cells[6].text)
                
                paper_info = {
                    'title': title,
                    'arxiv_id': arxiv_id,
                    'lhcb_paper_id': cells[3].text.strip(),
                    'journal': cells[5].text.strip(),
                    'working_groups': working_groups,
                    'data_taking_years': years,
                    'run_period': determine_run_period(years)
                }
                page_papers.append(paper_info)
                logger.debug(f"Parsed paper: {paper_info['lhcb_paper_id']} - {title[:50]}...")
            except Exception as e:
                logger.error(f"Error parsing row: {e}")
                continue
    
    return page_papers

def scrape_papers(max_papers: Optional[int] = None) -> List[dict]:
    """Scrape papers from LHCb publication page"""
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    driver = webdriver.Chrome(options=options)
    
    all_papers = []
    
    try:
        logger.info("Loading LHCb publication page...")
        driver.get('https://lbfence.cern.ch/alcm/public/analysis')
        
        wait = WebDriverWait(driver, 10)
        table = wait.until(EC.presence_of_element_located((By.TAG_NAME, "table")))
        
        # HACK: Initialize InspireClient for citation fetching - this is a hack to get the citations and integrate them into the paper object
        config = CorpusConfig(
            start_date=None,
            end_date=None,
            max_papers=max_papers,
            download=False,
            output_dir=Path("data"),
            verbose=False
        )
        inspire_client = CorpusBuilder(config).client
        
        while True:
            logger.info("Processing current page...")
            page_papers = process_page(driver)
            
            # Fetch citations for each paper
            for paper in page_papers:
                if paper['arxiv_id']:
                    try:
                        paper_data = inspire_client.fetch_paper_metadata(paper['arxiv_id'])
                        paper['citations'] = paper_data.get('citations', 0) if paper_data else 0
                        logger.debug(f"Paper {paper['arxiv_id']} has {paper['citations']} citations")
                    except Exception as e:
                        logger.warning(f"Failed to fetch citations for {paper['arxiv_id']}: {e}")
                        paper['citations'] = 0
                else:
                    paper['citations'] = 0
            
            all_papers.extend(page_papers)
            
            if max_papers and len(all_papers) >= max_papers:
                logger.info(f"Reached limit of {max_papers} papers.")
                break
            
            try:
                next_button = driver.find_element(By.XPATH, "//button[@aria-label='Next page']")
                if not next_button or 'disabled' in next_button.get_attribute('class'):
                    logger.info("Reached last page")
                    break
                    
                next_button.click()
                logger.debug("Moving to next page...")
                sleep(1)
                
            except Exception as e:
                logger.info("No more pages found")
                break
    
    except Exception as e:
        logger.error(f"Error scraping: {e}")
    
    finally:
        driver.quit()
    
    return all_papers

def build_corpus_from_scrape(papers: List[dict], output_dir: Path, verbose: bool = False) -> None:
    """Build corpus using scraped papers data, downloading the papers and saving them to the output directory"""
    config = CorpusConfig(
        start_date=None,
        end_date=None,
        max_papers=len(papers),
        download=True,  
        output_dir=output_dir,
        verbose=verbose
    )
    
    builder = CorpusBuilder(config)
    inspire_client = builder.client  # Get the InspireClient instance
    
    # Convert scraped paper data to LHCbPaper objects
    lhcb_papers = []
    for paper in papers:
        if paper['arxiv_id']:  # Only process papers with arXiv IDs
            # Fetch citation count from INSPIRE for this paper
            try:
                paper_data = inspire_client.fetch_paper_metadata(paper['arxiv_id'])
                citations = paper_data.get('citations', 0) if paper_data else 0
            except Exception as e:
                logger.warning(f"Failed to fetch citations for {paper['arxiv_id']}: {e}")
                citations = 0
                
            paper_obj = LHCbPaper(
                title=paper['title'],
                arxiv_id=paper['arxiv_id'],
                citations=citations
            )
            lhcb_papers.append(paper_obj)
            logger.debug(f"Paper {paper['arxiv_id']} has {citations} citations")
    
    # Download papers
    if config.download:
        failed_downloads = []
        for paper in tqdm(lhcb_papers, desc="Downloading and unpacking LHCb papers"):
            try:
                success = builder.download_paper(paper)
                if not success:
                    failed_downloads.append(paper)
            except Exception as e:
                failed_downloads.append(paper)
                logger.error(f"Error downloading paper '{paper.title}': {str(e)}")

def main():
    """Main function to scrape papers and build corpus"""
    parser = argparse.ArgumentParser(description="Scrape LHCb papers.")
    parser.add_argument('--max_papers', type=int, help='Maximum number of papers to scrape', default=None)
    args = parser.parse_args()
    
    papers = scrape_papers(max_papers=args.max_papers)
    logger.info(f"Successfully scraped {len(papers)} papers")
    
    # Save metadata with citations
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    df = pd.DataFrame(papers)
    
    # Save both pickle and CSV formats
    df.to_pickle(f'lhcb_papers_{timestamp}.pkl')
    df.to_csv(f'lhcb_papers_{timestamp}.csv', index=False)
    logger.info(f"Saved paper metadata to lhcb_papers_{timestamp}.pkl and .csv")
    
    # Build corpus
    output_dir = Path("data")
    build_corpus_from_scrape(papers, output_dir, verbose=True)

if __name__ == "__main__":
    main()