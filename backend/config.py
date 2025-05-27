"""
Configuration settings for the Knowledge Graph API.
"""

import os
from pathlib import Path
from typing import List, Dict, Any

# Base directories
BASE_DIR = Path(__file__).parent
PROJECT_ROOT = BASE_DIR.parent
UPLOAD_DIR = BASE_DIR / "uploaded_pdfs"
LOGS_DIR = BASE_DIR / "logs"

# API Configuration
API_TITLE = "Knowledge Graph API"
API_DESCRIPTION = "API for extracting knowledge graphs from PDF documents"
API_VERSION = "1.0.0"
API_HOST = "0.0.0.0"
API_PORT = 8000

# File upload settings
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
ALLOWED_EXTENSIONS = {".pdf"}
TEXT_PREVIEW_LENGTH = 300

# Ollama configuration
OLLAMA_MODELS = ["mistral:7b", "mistral", "llama2", "llama2:7b"]
OLLAMA_TIMEOUT = 30
MAX_TEXT_LENGTH = 1500
MAX_RELATIONSHIPS = 10

# Graph visualization settings
GRAPH_LAYOUTS = ["force", "hierarchical", "circular"]
DEFAULT_LAYOUT = "force"

# Semantic Scholar API settings
SEMANTIC_SCHOLAR_BASE_URL = "https://api.semanticscholar.org/graph/v1"
SEMANTIC_SCHOLAR_TIMEOUT = 10
SEMANTIC_SCHOLAR_MAX_RESULTS = 20
SEMANTIC_SCHOLAR_RATE_LIMIT = 1  # seconds between requests

# Logging configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_FILE = LOGS_DIR / "api.log"

# CORS settings
CORS_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:8080",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:8080",
    "*"  # Remove in production
]

# Graph processing settings
GRAPH_PROCESSING = {
    "min_text_length": 100,
    "chunk_size": 1000,
    "max_nodes": 100,
    "max_edges": 200,
    "node_size_range": (20, 60),
    "edge_width_range": (1, 5)
}

# Filtering settings
FILTER_SETTINGS = {
    "generic_terms": {
        'data', 'method', 'result', 'results', 'study', 'research', 'analysis',
        'approach', 'technique', 'process', 'system', 'model', 'framework',
        'paper', 'article', 'work', 'information', 'knowledge', 'concept',
        'idea', 'thing', 'item', 'element', 'factor', 'aspect', 'feature',
        'component', 'part', 'section', 'chapter', 'document', 'text'
    },
    "generic_relations": {
        'relates to', 'connected to', 'associated with', 'linked to',
        'mentioned with', 'appears with', 'found in', 'seen in'
    },
    "min_concept_length": 2,
    "max_concept_length": 50
}

# Color schemes for visualization
COLOR_SCHEMES = {
    "default": {
        "high_importance": "#FF6B6B",
        "medium_importance": "#4ECDC4",
        "low_importance": "#45B7D1",
        "background": "#fafafa"
    },
    "dark": {
        "high_importance": "#FF5722",
        "medium_importance": "#00BCD4",
        "low_importance": "#3F51B5",
        "background": "#263238"
    }
}

# Edge colors for different relationship types
EDGE_COLORS = {
    'enables': '#4CAF50',
    'improves': '#2196F3',
    'ensures': '#FF9800',
    'spans': '#9C27B0',
    'shows': '#F44336',
    'created for': '#795548',
    'facilitates': '#607D8B',
    'emphasizes': '#E91E63',
    'encountered': '#FF5722',
    'highlights': '#3F51B5',
    'uses': '#009688',
    'requires': '#FFC107',
    'implements': '#8BC34A',
    'relates_to': '#666666',
    'analyzes': '#E91E63',
    'generates': '#8BC34A',
    'depends_on': '#FF5722',
    'contains': '#9C27B0',
    'produces': '#4CAF50'
}

def get_config() -> Dict[str, Any]:
    """Get all configuration as a dictionary."""
    return {
        "api": {
            "title": API_TITLE,
            "description": API_DESCRIPTION,
            "version": API_VERSION,
            "host": API_HOST,
            "port": API_PORT
        },
        "files": {
            "max_size": MAX_FILE_SIZE,
            "allowed_extensions": list(ALLOWED_EXTENSIONS),
            "upload_dir": str(UPLOAD_DIR),
            "logs_dir": str(LOGS_DIR)
        },
        "ollama": {
            "models": OLLAMA_MODELS,
            "timeout": OLLAMA_TIMEOUT,
            "max_text_length": MAX_TEXT_LENGTH,
            "max_relationships": MAX_RELATIONSHIPS
        },
        "graph": {
            "layouts": GRAPH_LAYOUTS,
            "default_layout": DEFAULT_LAYOUT,
            "processing": GRAPH_PROCESSING,
            "colors": COLOR_SCHEMES,
            "edge_colors": EDGE_COLORS
        },
        "semantic_scholar": {
            "base_url": SEMANTIC_SCHOLAR_BASE_URL,
            "timeout": SEMANTIC_SCHOLAR_TIMEOUT,
            "max_results": SEMANTIC_SCHOLAR_MAX_RESULTS,
            "rate_limit": SEMANTIC_SCHOLAR_RATE_LIMIT
        },
        "cors": {
            "origins": CORS_ORIGINS
        },
        "logging": {
            "level": LOG_LEVEL,
            "format": LOG_FORMAT,
            "file": str(LOG_FILE)
        },
        "filtering": FILTER_SETTINGS
    }

def setup_directories():
    """Create necessary directories if they don't exist."""
    UPLOAD_DIR.mkdir(exist_ok=True)
    LOGS_DIR.mkdir(exist_ok=True)

def validate_config():
    """Validate configuration settings."""
    errors = []
    
    # Check required directories
    if not BASE_DIR.exists():
        errors.append(f"Base directory does not exist: {BASE_DIR}")
    
    # Check file size limits
    if MAX_FILE_SIZE <= 0:
        errors.append("MAX_FILE_SIZE must be positive")
    
    # Check Ollama timeout
    if OLLAMA_TIMEOUT <= 0:
        errors.append("OLLAMA_TIMEOUT must be positive")
    
    # Check API port
    if not (1 <= API_PORT <= 65535):
        errors.append("API_PORT must be between 1 and 65535")
    
    if errors:
        raise ValueError(f"Configuration errors: {'; '.join(errors)}")
    
    return True

# Environment-specific overrides
if os.getenv("ENVIRONMENT") == "production":
    # Production settings
    CORS_ORIGINS = [
        "https://yourdomain.com",
        "https://www.yourdomain.com"
    ]
    LOG_LEVEL = "WARNING"
    API_HOST = "0.0.0.0"

elif os.getenv("ENVIRONMENT") == "development":
    # Development settings
    LOG_LEVEL = "DEBUG"
    API_HOST = "127.0.0.1"

# Initialize configuration
if __name__ == "__main__":
    setup_directories()
    validate_config()
    print("Configuration validated successfully!")
    
    config = get_config()
    import json
    print(json.dumps(config, indent=2))