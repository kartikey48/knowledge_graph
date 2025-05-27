"""
Semantic Scholar API integration for paper search and retrieval.
"""
import requests
import logging
from typing import List, Dict, Any, Optional
import time

logger = logging.getLogger(__name__)

# Semantic Scholar API configuration
BASE_URL = "https://api.semanticscholar.org/graph/v1"
HEADERS = {
    "User-Agent": "Knowledge-Graph-App/1.0 (your-email@example.com)"
}

# Rate limiting
RATE_LIMIT_DELAY = 0.1  # 100ms between requests
last_request_time = 0

def rate_limit():
    """Simple rate limiting to respect API limits."""
    global last_request_time
    current_time = time.time()
    time_since_last = current_time - last_request_time
    
    if time_since_last < RATE_LIMIT_DELAY:
        time.sleep(RATE_LIMIT_DELAY - time_since_last)
    
    last_request_time = time.time()

def get_paper_details(paper_id: str) -> Optional[Dict[str, Any]]:
    """
    Get detailed information about a specific paper.
    """
    try:
        rate_limit()
        
        url = f"{BASE_URL}/paper/{paper_id}"
        params = {
            "fields": "paperId,title,abstract,authors,year,venue,citationCount,url,openAccessPdf,references,citations"
        }
        
        logger.info(f"Getting details for paper: {paper_id}")
        
        response = requests.get(url, params=params, headers=HEADERS, timeout=10)
        response.raise_for_status()
        
        paper_data = response.json()
        processed_paper = process_paper_data(paper_data)
        
        logger.info(f"Retrieved details for paper: {paper_data.get('title', 'Unknown')}")
        return processed_paper
        
    except requests.exceptions.RequestException as e:
        logger.error(f"API request failed for paper {paper_id}: {e}")
        return None
    except Exception as e:
        logger.error(f"Error getting paper details: {e}")
        return None

def get_related_papers_by_domain(query: str, domain: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Search for papers related to a query in a specific domain.
    """
    try:
        rate_limit()
        
        # Construct search query
        search_query = f"{query} {domain}"
        
        # API endpoint for paper search
        url = f"{BASE_URL}/paper/search"
        
        params = {
            "query": search_query,
            "limit": limit,
            "fields": "paperId,title,abstract,authors,year,venue,citationCount,url,openAccessPdf"
        }
        
        logger.info(f"Searching papers for query: '{search_query}'")
        
        response = requests.get(url, params=params, headers=HEADERS, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        papers = data.get("data", [])
        
        # Process and clean the results
        processed_papers = []
        for paper in papers:
            processed_paper = process_paper_data(paper)
            if processed_paper:
                processed_papers.append(processed_paper)
        
        logger.info(f"Found {len(processed_papers)} papers for query: '{search_query}'")
        return processed_papers
        
    except requests.exceptions.RequestException as e:
        logger.error(f"API request failed: {e}")
        return []
    except Exception as e:
        logger.error(f"Error searching papers: {e}")
        return []

def get_papers_by_author(author_name: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Get papers by a specific author.
    """
    try:
        rate_limit()
        
        # First, search for the author
        author_url = f"{BASE_URL}/author/search"
        author_params = {
            "query": author_name,
            "limit": 1
        }
        
        logger.info(f"Searching for author: '{author_name}'")
        
        author_response = requests.get(author_url, params=author_params, headers=HEADERS, timeout=10)
        author_response.raise_for_status()
        
        author_data = author_response.json()
        authors = author_data.get("data", [])
        
        if not authors:
            logger.warning(f"No author found for: '{author_name}'")
            return []
        
        author_id = authors[0]["authorId"]
        
        # Get papers by this author
        papers_url = f"{BASE_URL}/author/{author_id}/papers"
        papers_params = {
            "limit": limit,
            "fields": "paperId,title,abstract,authors,year,venue,citationCount,url,openAccessPdf"
        }
        
        papers_response = requests.get(papers_url, params=papers_params, headers=HEADERS, timeout=10)
        papers_response.raise_for_status()
        
        papers_data = papers_response.json()
        papers = papers_data.get("data", [])
        
        # Process and clean the results
        processed_papers = []
        for paper in papers:
            processed_paper = process_paper_data(paper)
            if processed_paper:
                processed_papers.append(processed_paper)
        
        logger.info(f"Found {len(processed_papers)} papers for author: '{author_name}'")
        return processed_papers
        
    except requests.exceptions.RequestException as e:
        logger.error(f"API request failed: {e}")
        return []
    except Exception as e:
        logger.error(f"Error getting papers by author: {e}")
        return []

def process_paper_data(paper: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Process and clean paper data from the API response.
    """
    try:
        if not paper:
            return None
        
        # Extract basic information
        processed = {
            "paperId": paper.get("paperId"),
            "title": paper.get("title", "").strip(),
            "abstract": paper.get("abstract", "").strip() if paper.get("abstract") else None,
            "year": paper.get("year"),
            "venue": paper.get("venue", "").strip() if paper.get("venue") else None,
            "citationCount": paper.get("citationCount", 0),
            "url": paper.get("url")
        }
        
        # Process authors
        authors = paper.get("authors", [])
        if authors:
            processed["authors"] = [author.get("name", "").strip() for author in authors if author.get("name")]
        else:
            processed["authors"] = []
        
        # Try to get PDF URL
        pdf_url = None
        open_access_pdf = paper.get("openAccessPdf")
        if open_access_pdf and open_access_pdf.get("url"):
            pdf_url = open_access_pdf["url"]
        
        processed["pdfUrl"] = pdf_url
        
        # Clean up empty fields
        if not processed["title"]:
            return None
        
        # Truncate abstract if too long
        if processed["abstract"] and len(processed["abstract"]) > 1000:
            processed["abstract"] = processed["abstract"][:1000] + "..."
        
        return processed
        
    except Exception as e:
        logger.warning(f"Error processing paper data: {e}")
        return None

def search_papers_by_keywords(keywords: List[str], limit: int = 10) -> List[Dict[str, Any]]:
    """
    Search for papers using a list of keywords.
    """
    try:
        # Join keywords into a search query
        query = " ".join(keywords)
        
        url = f"{BASE_URL}/paper/search"
        params = {
            "query": query,
            "limit": limit,
            "fields": "title,abstract,authors,year,citationCount,url,paperId"
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        papers = data.get("data", [])
        
        # Format results
        formatted_papers = []
        for paper in papers:
            formatted_paper = {
                "title": paper.get("title", "Unknown Title"),
                "abstract": paper.get("abstract", "No abstract available")[:300] + "..." if paper.get("abstract") else "No abstract available",
                "authors": [author.get("name", "Unknown") for author in paper.get("authors", [])],
                "year": paper.get("year"),
                "citation_count": paper.get("citationCount", 0),
                "url": paper.get("url"),
                "paper_id": paper.get("paperId")
            }
            formatted_papers.append(formatted_paper)
        
        logger.info(f"Found {len(formatted_papers)} papers for keywords: {keywords}")
        return formatted_papers
        
    except requests.exceptions.RequestException as e:
        logger.error(f"API request failed: {e}")
        return []
    except Exception as e:
        logger.error(f"Error searching papers by keywords: {e}")
        return []

def search_papers_advanced(
    query: str,
    fields_of_study: List[str] = None,
    year_range: tuple = None,
    min_citations: int = None,
    limit: int = 10
) -> List[Dict[str, Any]]:
    """
    Advanced paper search with additional filters.
    """
    try:
        rate_limit()
        
        # Build search parameters
        params = {
            "query": query,
            "limit": limit,
            "fields": "paperId,title,abstract,authors,year,venue,citationCount,url,openAccessPdf,fieldsOfStudy"
        }
        
        # Add filters if provided
        if year_range:
            start_year, end_year = year_range
            params["year"] = f"{start_year}-{end_year}"
        
        if min_citations:
            params["minCitationCount"] = min_citations
        
        if fields_of_study:
            params["fieldsOfStudy"] = ",".join(fields_of_study)
        
        url = f"{BASE_URL}/paper/search"
        
        logger.info(f"Advanced search for: '{query}' with filters")
        
        response = requests.get(url, params=params, headers=HEADERS, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        papers = data.get("data", [])
        
        # Process results
        processed_papers = []
        for paper in papers:
            processed_paper = process_paper_data(paper)
            if processed_paper:
                processed_papers.append(processed_paper)
        
        logger.info(f"Advanced search found {len(processed_papers)} papers")
        return processed_papers
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Advanced search API request failed: {e}")
        return []
    except Exception as e:
        logger.error(f"Error in advanced search: {e}")
        return []

def get_paper_recommendations(paper_id: str, limit: int = 5) -> List[Dict[str, Any]]:
    """
    Get recommended papers based on a given paper.
    """
    try:
        rate_limit()
        
        # Get paper details first to understand the context
        paper_details = get_paper_details(paper_id)
        if not paper_details:
            return []
        
        # Use the paper's title and abstract for finding similar papers
        search_query = paper_details.get("title", "")
        if paper_details.get("abstract"):
            # Use first 100 characters of abstract
            search_query += " " + paper_details["abstract"][:100]
        
        # Search for similar papers
        url = f"{BASE_URL}/paper/search"
        params = {
            "query": search_query,
            "limit": limit + 5,  # Get more to filter out the original paper
            "fields": "paperId,title,abstract,authors,year,venue,citationCount,url,openAccessPdf"
        }
        
        response = requests.get(url, params=params, headers=HEADERS, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        papers = data.get("data", [])
        
        # Process and filter out the original paper
        recommendations = []
        for paper in papers:
            if paper.get("paperId") != paper_id:  # Exclude the original paper
                processed_paper = process_paper_data(paper)
                if processed_paper:
                    recommendations.append(processed_paper)
                    if len(recommendations) >= limit:
                        break
        
        logger.info(f"Found {len(recommendations)} recommendations for paper {paper_id}")
        return recommendations
        
    except Exception as e:
        logger.error(f"Error getting paper recommendations: {e}")
        return []

def get_trending_papers(field: str = "computer science", limit: int = 10) -> List[Dict[str, Any]]:
    """
    Get trending papers in a specific field (papers with high recent citation growth).
    """
    try:
        rate_limit()
        
        # Search for recent papers with high citation counts
        current_year = 2024
        search_query = f"field:{field}"
        
        url = f"{BASE_URL}/paper/search"
        params = {
            "query": search_query,
            "year": f"{current_year-2}-{current_year}",  # Last 2 years
            "minCitationCount": 10,
            "limit": limit,
            "sort": "citationCount:desc",
            "fields": "paperId,title,abstract,authors,year,venue,citationCount,url,openAccessPdf"
        }
        
        response = requests.get(url, params=params, headers=HEADERS, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        papers = data.get("data", [])
        
        # Process results
        trending_papers = []
        for paper in papers:
            processed_paper = process_paper_data(paper)
            if processed_paper:
                trending_papers.append(processed_paper)
        
        logger.info(f"Found {len(trending_papers)} trending papers in {field}")
        return trending_papers
        
    except Exception as e:
        logger.error(f"Error getting trending papers: {e}")
        return []

# Utility functions for testing
def test_api_connection() -> bool:
    """
    Test if the Semantic Scholar API is accessible.
    """
    try:
        rate_limit()
        
        # Simple test query
        url = f"{BASE_URL}/paper/search"
        params = {
            "query": "machine learning",
            "limit": 1,
            "fields": "paperId,title"
        }
        
        response = requests.get(url, params=params, headers=HEADERS, timeout=5)
        response.raise_for_status()
        
        data = response.json()
        papers = data.get("data", [])
        
        if papers:
            logger.info("Semantic Scholar API connection successful")
            return True
        else:
            logger.warning("Semantic Scholar API returned no results")
            return False
            
    except Exception as e:
        logger.error(f"Semantic Scholar API connection failed: {e}")
        return False

if __name__ == "__main__":
    # Test the API functions
    print("Testing Semantic Scholar API...")
    
    # Test connection
    if test_api_connection():
        print("✅ API connection successful")
        
        # Test search
        papers = get_related_papers_by_domain("neural networks", "machine learning", limit=3)
        print(f"✅ Found {len(papers)} papers for 'neural networks' in 'machine learning'")
        
        if papers:
            print(f"Sample paper: {papers[0]['title']}")
        
        # Test author search
        author_papers = get_papers_by_author("Geoffrey Hinton", limit=3)
        print(f"✅ Found {len(author_papers)} papers by 'Geoffrey Hinton'")
        
    else:
        print("❌ API connection failed")
