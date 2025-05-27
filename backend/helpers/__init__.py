"""
Helper modules for the knowledge graph backend.
"""

# Import functions that are available
from .semantic_scholar import (
    get_related_papers_by_domain, 
    get_papers_by_author, 
    get_paper_details,
    search_papers_by_keywords
)

__all__ = [
    'get_related_papers_by_domain',
    'get_papers_by_author', 
    'get_paper_details',
    'search_papers_by_keywords'
]
