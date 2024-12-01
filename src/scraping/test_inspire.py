from pathlib import Path
from inspire import InspireClient

# Create directories for storing papers
current_dir = Path.cwd()  # Gets current working directory
pdf_directory = current_dir / "papers_pdf"
source_directory = current_dir / "papers_source"

# Initialize the client
client = InspireClient(pdf_dir=pdf_directory, source_dir=source_directory)

# Fetch papers (let's start with 5 for testing)
papers = client.fetch_papers(max_results=5)

# # Print out what we found
# for paper in papers:
#     print(f"\nTitle: {paper.title}")
#     print(f"Citations: {paper.citations}")
#     print(f"arXiv ID: {paper.arxiv_id}")
    
#     # Try downloading PDF and source if available
#     pdf_path = client.download_pdf(paper)
#     source_path = client.download_source(paper)
    
#     if pdf_path:
#         print(f"PDF downloaded to: {pdf_path}")
#     if source_path:
#         print(f"Source downloaded to: {source_path}")