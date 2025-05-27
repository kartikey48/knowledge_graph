import sys
import os
from pathlib import Path
from typing import List, Dict, Any, Optional, Union
from contextlib import asynccontextmanager
import asyncio
import uuid
import traceback
import logging
import time
from io import BytesIO
import tempfile
import urllib.request
from urllib.parse import urlparse

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configuration
USE_OLLAMA = os.getenv("USE_OLLAMA", "false").lower() == "true"
FALLBACK_TO_RULES = os.getenv("FALLBACK_TO_RULES", "true").lower() == "true"

from backend.helpers.pdf_parser import extract_concepts_with_relationships_safe
from fastapi import FastAPI, UploadFile, File, Query, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from pydantic import BaseModel, Field
import shutil
import fitz  # PyMuPDF

# Import your custom modules
try:
    from backend.extractor import extract_concepts_with_relationships
    from backend.helpers.semantic_scholar import get_related_papers_by_domain, get_papers_by_author
except ImportError as e:
    logging.error(f"Failed to import backend modules: {e}")
    # Create dummy functions for development
    async def extract_concepts_with_relationships(text: str) -> List[Dict[str, Any]]:
        return [{"source": "test", "target": "concept", "relation": "example"}]
    
    async def get_related_papers_by_domain(node: str, domain: str) -> List[Dict[str, Any]]:
        return [{"title": "Sample Paper", "abstract": "Sample abstract"}]
    
    async def get_papers_by_author(author: str) -> List[Dict[str, Any]]:
        return [{"title": "Sample Paper", "abstract": "Sample abstract"}]

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
UPLOAD_DIR = Path("uploaded_pdfs")
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
ALLOWED_EXTENSIONS = {".pdf"}
TEXT_PREVIEW_LENGTH = 300
# Pydantic models
class UploadResponse(BaseModel):
    metadata: Dict[str, Any]
    graph: List[Dict[str, Any]]

class EnhancedUploadResponse(BaseModel):
    success: bool
    metadata: Dict[str, Any]
    graph: List[Dict[str, Any]]
    processing_time: float
    analysis: Optional[Dict[str, Any]] = None
    debug_info: Optional[Dict[str, Any]] = None

class QueryResponse(BaseModel):
    results: List[Dict[str, Any]]

class ErrorResponse(BaseModel):
    detail: str

class GraphNode(BaseModel):
    data: Dict[str, str] = Field(..., description="Node data with id and label")

class GraphEdge(BaseModel):
    data: Dict[str, str] = Field(..., description="Edge data with source, target, and label")

class Relationship(BaseModel):
    source: str
    target: str
    relation: str
    
    def to_dict(self) -> Dict[str, str]:
        """Convert relationship to dictionary format."""
        return {
            "source": self.source,
            "target": self.target,
            "relation": self.relation
        }

class DomainSearchRequest(BaseModel):
    node: str = Field(..., description="Node/concept to search for")
    domain: str = Field(..., description="Domain/field to search within")

class PaperGraphRequest(BaseModel):
    paper_id: str = Field(..., description="Paper ID to generate graph for")
    paper_url: Optional[str] = Field(None, description="Paper URL if available")

class NodeInteractionResponse(BaseModel):
    success: bool
    node: str
    domain: str
    papers: List[Dict[str, Any]]
    total_found: int

class PaperGraphResponse(BaseModel):
    success: bool
    paper_info: Dict[str, Any]
    graph: List[Dict[str, Any]]
    metadata: Dict[str, Any]

class GraphStats(BaseModel):
    num_nodes: int
    num_edges: int
    density: float
    avg_degree: float
    central_concepts: List[Dict[str, Any]]
# Startup/shutdown events
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    UPLOAD_DIR.mkdir(exist_ok=True)
    logger.info("Application started successfully")
    yield
    # Shutdown
    logger.info("Application shutting down")

# Initialize FastAPI app
app = FastAPI(
    title="Enhanced Knowledge Graph API",
    description="API for extracting knowledge graphs from PDF documents with enhanced processing",
    version="2.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Consider restricting this in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# Enhanced middleware for request logging
@app.middleware("http")
async def log_requests(request, call_next):
    start_time = time.time()
    
    # Generate request ID for tracking
    request_id = str(uuid.uuid4())[:8]
    
    # Log request
    logger.info(f"Request [{request_id}]: {request.method} {request.url}")
    
    try:
        response = await call_next(request)
        process_time = time.time() - start_time
        
        # Log response
        logger.info(f"Response [{request_id}]: {response.status_code} - {process_time:.3f}s")
        
        # Add custom headers
        response.headers["X-Process-Time"] = str(process_time)
        response.headers["X-Request-ID"] = request_id
        
        return response
        
    except Exception as e:
        process_time = time.time() - start_time
        logger.error(f"Request [{request_id}] failed after {process_time:.3f}s: {str(e)}")
        raise

# Utility functions
def validate_file(file: UploadFile) -> None:
    """Validate uploaded file."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")
    
    file_extension = Path(file.filename).suffix.lower()
    if file_extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400, 
            detail=f"Only {', '.join(ALLOWED_EXTENSIONS)} files are allowed"
        )

async def save_uploaded_file(file: UploadFile) -> Path:
    """Save uploaded file to disk."""
    file_id = str(uuid.uuid4())
    file_path = UPLOAD_DIR / f"{file_id}_{file.filename}"
    
    try:
        with open(file_path, "wb") as f:
            content = await file.read()
            if len(content) > MAX_FILE_SIZE:
                raise HTTPException(
                    status_code=413, 
                    detail=f"File too large. Maximum size is {MAX_FILE_SIZE // (1024*1024)}MB"
                )
            f.write(content)
        return file_path
    except Exception as e:
        logger.error(f"Error saving file: {e}")
        if file_path.exists():
            file_path.unlink()  # Clean up on error
        raise HTTPException(status_code=500, detail="Failed to save file")

def extract_text_from_pdf(file_path: Path) -> str:
    """Extract text from PDF file."""
    try:
        with open(file_path, "rb") as f:
            doc = fitz.open(stream=f.read(), filetype="pdf")
            
        text_parts = []
        for page_num, page in enumerate(doc):
            try:
                page_text = page.get_text()
                if page_text.strip():
                    text_parts.append(page_text)
            except Exception as e:
                logger.warning(f"Error extracting text from page {page_num}: {e}")
                continue
        
        doc.close()
        
        if not text_parts:
            raise ValueError("No readable text found in the PDF")
            
        return "\n".join(text_parts)
        
    except Exception as e:
        logger.error(f"Error extracting text from PDF: {e}")
        raise HTTPException(status_code=422, detail="Failed to extract text from PDF")

def validate_relationships(relationships: List[Dict[str, Any]]) -> List[Relationship]:
    """Validate and clean relationship data."""
    valid_relationships = []
    
    for rel in relationships:
        try:
            # Validate required fields
            source = rel.get("source", "").strip()
            target = rel.get("target", "").strip()
            relation = rel.get("relation", "").strip()
            
            if source and target and relation and source != target:
                valid_relationships.append(Relationship(
                    source=source,
                    target=target,
                    relation=relation
                ))
            else:
                logger.debug(f"Skipping invalid relationship: {rel}")
                
        except Exception as e:
            logger.warning(f"Error validating relationship {rel}: {e}")
            continue
    
    return valid_relationships

def format_for_cytoscape(relationships: List[Relationship]) -> List[Dict[str, Any]]:
    """Format relationships for Cytoscape visualization."""
    nodes = {}
    elements = []
    
    for rel in relationships:
        # Convert to dict if it's a Relationship object
        rel_dict = rel.to_dict() if isinstance(rel, Relationship) else rel
        
        source = rel_dict["source"]
        target = rel_dict["target"]
        relation = rel_dict["relation"]
        
        # Add nodes if not already present
        if source not in nodes:
            nodes[source] = {
                "data": {
                    "id": source,
                    "label": source,
                    "type": "concept"
                }
            }
        
        if target not in nodes:
            nodes[target] = {
                "data": {
                    "id": target,
                    "label": target,
                    "type": "concept"
                }
            }
        
        # Add edge
        edge_id = f"{source}-{target}-{relation}"
        elements.append({
            "data": {
                "id": edge_id,
                "source": source,
                "target": target,
                "label": relation,
                "type": "relationship"
            }
        })
    
    return list(nodes.values()) + elements

def chunk_text(text: str, chunk_size: int = 1500, chunk_overlap: int = 150) -> List[str]:
    """Split text into overlapping chunks for better processing."""
    if len(text) <= chunk_size:
        return [text]
    
    chunks = []
    start = 0
    
    while start < len(text):
        end = start + chunk_size
        
        # Try to break at sentence boundary
        if end < len(text):
            # Look for sentence endings within the last 200 characters
            last_period = text.rfind('.', end - 200, end)
            last_exclamation = text.rfind('!', end - 200, end)
            last_question = text.rfind('?', end - 200, end)
            
            sentence_end = max(last_period, last_exclamation, last_question)
            if sentence_end > start:
                end = sentence_end + 1
        
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        
        start = end - chunk_overlap
        
        # Prevent infinite loop
        if start >= len(text):
            break
    
    return chunks

def analyze_graph_structure(relationships: List[Union[Relationship, Dict[str, Any]]]) -> Dict[str, Any]:
    """
    Analyze the graph structure to provide insights about the knowledge graph.
    Works with both Relationship objects and dictionaries.
    """
    # Extract source and target from each relationship
    sources_targets = []
    for rel in relationships:
        if isinstance(rel, Relationship):
            sources_targets.append((rel.source, rel.target))
        else:
            # Handle dictionary format (for Cytoscape elements)
            if "data" in rel and "source" in rel["data"]:
                sources_targets.append((rel["data"]["source"], rel["data"]["target"]))
            elif "source" in rel and "target" in rel:
                sources_targets.append((rel["source"], rel["target"]))
    
    # Get unique nodes
    all_nodes = set()
    for source, target in sources_targets:
        all_nodes.add(source)
        all_nodes.add(target)
    
    # Calculate basic graph metrics
    num_nodes = len(all_nodes)
    num_edges = len(sources_targets)
    
    if num_nodes == 0:
        return {
            "num_nodes": 0,
            "num_edges": 0,
            "density": 0,
            "avg_degree": 0,
            "central_concepts": []
        }
    
    # Calculate graph density
    max_possible_edges = num_nodes * (num_nodes - 1) / 2
    density = num_edges / max_possible_edges if max_possible_edges > 0 else 0
    
    # Calculate average degree
    avg_degree = (2 * num_edges) / num_nodes if num_nodes > 0 else 0
    
    # Find central concepts (nodes with highest degree)
    node_degrees = {}
    for source, target in sources_targets:
        node_degrees[source] = node_degrees.get(source, 0) + 1
        node_degrees[target] = node_degrees.get(target, 0) + 1
    
    # Get top 5 central concepts
    central_concepts = sorted(
        [{"concept": node, "degree": degree} for node, degree in node_degrees.items()],
        key=lambda x: x["degree"],
        reverse=True
    )[:5]
    
    return {
        "num_nodes": num_nodes,
        "num_edges": num_edges,
        "density": density,
        "avg_degree": avg_degree,
        "central_concepts": central_concepts
    }

    
    # Calculate graph density
    max_possible_edges = num_nodes * (num_nodes - 1) / 2
    density = num_edges / max_possible_edges if max_possible_edges > 0 else 0
    
    # Calculate average degree
    avg_degree = (2 * num_edges) / num_nodes if num_nodes > 0 else 0
    
    # Find central concepts (nodes with highest degree)
    node_degrees = {}
    for source, target in sources_targets:
        node_degrees[source] = node_degrees.get(source, 0) + 1
        node_degrees[target] = node_degrees.get(target, 0) + 1
    
    # Get top 5 central concepts
    central_concepts = sorted(
        [{"concept": node, "degree": degree} for node, degree in node_degrees.items()],
        key=lambda x: x["degree"],
        reverse=True
    )[:5]
    
    return {
        "num_nodes": num_nodes,
        "num_edges": num_edges,
        "density": density,
        "avg_degree": avg_degree,
        "central_concepts": central_concepts
    }

async def cleanup_file(file_path: Path) -> None:
    """Clean up uploaded file."""
    try:
        if file_path.exists():
            file_path.unlink()
            logger.info(f"Cleaned up file: {file_path}")
    except Exception as e:
        logger.error(f"Error cleaning up file {file_path}: {e}")

# API Routes
@app.get("/", tags=["Health"])
async def root():
    """Health check endpoint with API overview."""
    return {
        "message": "Enhanced Knowledge Graph API is running",
        "version": "2.0.0",
        "features": [
            "PDF text extraction and processing",
            "Advanced concept and relationship extraction",
            "Enhanced graph analysis and visualization",
            "Chunked processing for large documents",
            "Graph structure analysis",
            "Multiple processing configurations"
        ],
        "endpoints": {
            "core": ["/upload", "/upload_enhanced"],
            "search": ["/query", "/author"],
            "future": ["/graph_by_paper"]
        },
        "supported_formats": ["PDF"],
        "max_file_size": "50MB"
    }

@app.post("/upload", response_model=UploadResponse, tags=["Knowledge Graph"])
async def upload_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="PDF file to process")
):
    """
    Upload a PDF file and extract knowledge graph.
    
    - **file**: PDF file to process (max 50MB)
    
    Returns the extracted knowledge graph in Cytoscape format.
    """
    file_path = None
    
    try:
        # Validate file
        validate_file(file)
        logger.info(f"Processing file: {file.filename}")
        
        # Save file
        file_path = await save_uploaded_file(file)
        
        # Extract text
        logger.info("Extracting text from PDF...")
        text = extract_text_from_pdf(file_path)
        
        if len(text.strip()) < 100:  # Minimum text threshold
            raise HTTPException(
                status_code=422, 
                detail="PDF contains insufficient text for processing"
            )
        
        logger.info(f"Text extraction successful. Length: {len(text)} characters")
        logger.debug(f"Sample text: {text[:TEXT_PREVIEW_LENGTH]}...")
        
        # Extract relationships
        logger.info("Extracting relationships...")
        raw_relationships = await asyncio.to_thread(
            extract_concepts_with_relationships_safe, text
        )
        
        if not isinstance(raw_relationships, list):
            raise ValueError("Relationship extraction failed")
        
        # Validate relationships
        relationships = validate_relationships(raw_relationships)
        
        if not relationships:
            raise HTTPException(
                status_code=422,
                detail="No valid relationships could be extracted from the document"
            )
        
        logger.info(f"Extracted {len(relationships)} valid relationships")
        
        # Format for visualization
        elements = format_for_cytoscape(relationships)
        
        # Analyze graph structure - pass relationships, not elements
        graph_analysis = analyze_graph_structure(relationships)
        
        # Prepare response
        metadata = {
            "filename": file.filename,
            "text_length": len(text),
            "num_relationships": len(relationships),
            "num_nodes": graph_analysis["num_nodes"],
            "num_edges": graph_analysis["num_edges"],
            "central_concepts": graph_analysis["central_concepts"]
        }
        
        # Schedule cleanup
        background_tasks.add_task(cleanup_file, file_path)
        
        return UploadResponse(metadata=metadata, graph=elements)
        
    except HTTPException:
        if file_path:
            background_tasks.add_task(cleanup_file, file_path)
        raise
    except Exception as e:
        logger.error(f"Unexpected error processing file: {e}")
        traceback.print_exc()
        if file_path:
            background_tasks.add_task(cleanup_file, file_path)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process file: {str(e)}"
        )
@app.post("/upload_enhanced", response_model=EnhancedUploadResponse, tags=["Knowledge Graph"])
async def upload_file_enhanced(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="PDF file to process"),
    chunk_size: int = Query(1500, ge=500, le=3000, description="Text chunk size for processing"),
    chunk_overlap: int = Query(150, ge=0, le=500, description="Overlap between text chunks"),
    max_relationships: int = Query(15, ge=5, le=50, description="Maximum relationships to extract"),
    enable_debug: bool = Query(False, description="Enable debug information in response"),
    export_formats: bool = Query(False, description="Include export format data")
):
    """
    Enhanced PDF upload with advanced processing options.
    
    - **file**: PDF file to process (max 50MB)
    - **chunk_size**: Size of text chunks for processing (500-3000 chars)
    - **chunk_overlap**: Overlap between chunks (0-500 chars)
    - **max_relationships**: Maximum relationships to extract (5-50)
    - **enable_debug**: Include debug information in response
    - **export_formats**: Include data for various export formats
    
    Returns enhanced knowledge graph with analysis and optional debug info.
    """
    start_time = time.time()
    file_path = None
    debug_info = {}
    
    try:
        # Validate file
        validate_file(file)
        logger.info(f"Enhanced processing for file: {file.filename}")
        
        if enable_debug:
            debug_info["processing_config"] = {
                "chunk_size": chunk_size,
                "chunk_overlap": chunk_overlap,
                "max_relationships": max_relationships
            }
        
        # Save file
        file_path = await save_uploaded_file(file)
        
        # Extract text
        logger.info("Extracting text from PDF...")
        text_extraction_start = time.time()
        text = extract_text_from_pdf(file_path)
        text_extraction_time = time.time() - text_extraction_start
        
        if len(text.strip()) < 100:
            raise HTTPException(
                status_code=422, 
                detail="PDF contains insufficient text for processing"
            )
        
        logger.info(f"Text extraction completed in {text_extraction_time:.2f}s. Length: {len(text)} characters")
        
        if enable_debug:
            debug_info["text_extraction"] = {
                "time_seconds": round(text_extraction_time, 2),
                "total_characters": len(text),
                "sample_text": text[:TEXT_PREVIEW_LENGTH] + "..." if len(text) > TEXT_PREVIEW_LENGTH else text
            }
        
        # Chunk text for processing
        chunks = chunk_text(text, chunk_size, chunk_overlap)
        logger.info(f"Text split into {len(chunks)} chunks")
        
        if enable_debug:
            debug_info["chunking"] = {
                "total_chunks": len(chunks),
                "chunk_sizes": [len(chunk) for chunk in chunks[:5]],  # First 5 chunk sizes
                "average_chunk_size": sum(len(chunk) for chunk in chunks) / len(chunks)
            }
        
        # Process chunks and extract relationships
        logger.info("Extracting relationships from chunks...")
        extraction_start = time.time()
        
        all_relationships = []
        chunk_results = []
        
        for i, chunk in enumerate(chunks[:5]):  # Limit to 5 chunks for performance
            logger.info(f"Processing chunk {i+1}/{min(len(chunks), 5)}")
            
            try:
                chunk_relationships = await asyncio.to_thread(
                    extract_concepts_with_relationships, chunk
                )
                
                if isinstance(chunk_relationships, list):
                    all_relationships.extend(chunk_relationships)
                    chunk_results.append({
                        "chunk_index": i,
                        "relationships_found": len(chunk_relationships),
                        "chunk_length": len(chunk)
                    })
                else:
                    logger.warning(f"Chunk {i} returned invalid data")
                    chunk_results.append({
                        "chunk_index": i,
                        "relationships_found": 0,
                        "chunk_length": len(chunk),
                        "error": "Invalid response format"
                    })
                    
            except Exception as e:
                logger.error(f"Error processing chunk {i}: {e}")
                chunk_results.append({
                    "chunk_index": i,
                    "relationships_found": 0,
                    "chunk_length": len(chunk),
                    "error": str(e)
                })
                continue
        
        extraction_time = time.time() - extraction_start
        logger.info(f"Relationship extraction completed in {extraction_time:.2f}s")
        
        if enable_debug:
            debug_info["extraction"] = {
                "time_seconds": round(extraction_time, 2),
                "chunks_processed": len(chunk_results),
                "chunk_results": chunk_results,
                "total_raw_relationships": len(all_relationships)
            }
        
        # Validate and filter relationships
        validation_start = time.time()
        relationships = validate_relationships(all_relationships)
        
        # Limit to max_relationships
        if len(relationships) > max_relationships:
            # Sort by some quality metric (for now, just take first N)
            relationships = relationships[:max_relationships]
        
        validation_time = time.time() - validation_start
        
        if not relationships:
            raise HTTPException(
                status_code=422,
                detail="No valid relationships could be extracted from the document"
            )
        
        logger.info(f"Validated {len(relationships)} relationships in {validation_time:.2f}s")
        
        if enable_debug:
            debug_info["validation"] = {
                "time_seconds": round(validation_time, 2),
                "raw_relationships": len(all_relationships),
                "valid_relationships": len(relationships),
                "filtered_relationships": len(relationships)
            }
        
        # Format for visualization
        formatting_start = time.time()
        elements = format_for_cytoscape(relationships)
        formatting_time = time.time() - formatting_start
        
        # Analyze graph structure - use relationships for analysis
        analysis_start = time.time()
        graph_analysis = analyze_graph_structure(relationships)
        analysis_time = time.time() - analysis_start
        
        total_processing_time = time.time() - start_time
        
        logger.info(f"Graph formatting completed in {formatting_time:.2f}s")
        logger.info(f"Graph analysis completed in {analysis_time:.2f}s")
        logger.info(f"Total processing time: {total_processing_time:.2f}s")
        
        # Prepare enhanced metadata
        metadata = {
            "filename": file.filename,
            "file_size_bytes": 0,  # We can't get this easily from UploadFile after reading
            "text_length": len(text),
            "chunks_processed": len(chunks),
            "processing_config": {
                "chunk_size": chunk_size,
                "chunk_overlap": chunk_overlap,
                "max_relationships": max_relationships
            },
            "extraction_stats": {
                "raw_relationships": len(all_relationships),
                "valid_relationships": len(relationships),
                "final_relationships": len(relationships)
            },
            "graph_stats": {
                "num_nodes": len([e for e in elements if "source" not in e["data"]]),
                "num_edges": len([e for e in elements if "source" in e["data"]])
            },
            "timing": {
                "text_extraction_seconds": round(text_extraction_time, 2),
                "relationship_extraction_seconds": round(extraction_time, 2),
                "validation_seconds": round(validation_time, 2),
                "formatting_seconds": round(formatting_time, 2),
                "analysis_seconds": round(analysis_time, 2),
                "total_seconds": round(total_processing_time, 2)
            }
        }
        
        # Add export formats if requested
        if export_formats:
            export_data = generate_export_formats(relationships, elements)
            metadata["export_formats"] = export_data
        
        # Schedule cleanup
        background_tasks.add_task(cleanup_file, file_path)
        
        response = EnhancedUploadResponse(
            success=True,
            metadata=metadata,
            graph=elements,
            processing_time=round(total_processing_time, 2),
            analysis=graph_analysis,
            debug_info=debug_info if enable_debug else None
        )
        
        return response
        
    except HTTPException:
        if file_path:
            background_tasks.add_task(cleanup_file, file_path)
        raise
    except Exception as e:
        logger.error(f"Unexpected error in enhanced processing: {e}")
        traceback.print_exc()
        if file_path:
            background_tasks.add_task(cleanup_file, file_path)
        
        # Return error response with partial debug info
        error_time = time.time() - start_time
        raise HTTPException(
            status_code=500,
            detail={
                "error": f"Failed to process file: {str(e)}",
                "processing_time": round(error_time, 2),
                "debug_info": debug_info if enable_debug else None
            }








        )
def generate_export_formats(relationships: List[Relationship], elements: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Generate data in various export formats."""
    
    # CSV format data
    csv_data = []
    for rel in relationships:
        csv_data.append({
            "source": rel.source,
            "target": rel.target,
            "relationship": rel.relation
        })
    
    # GraphML format structure
    nodes = [e for e in elements if "source" not in e["data"]]
    edges = [e for e in elements if "source" in e["data"]]
    
    graphml_structure = {
        "nodes": [{"id": node["data"]["id"], "label": node["data"]["label"]} for node in nodes],
        "edges": [{"source": edge["data"]["source"], "target": edge["data"]["target"], "label": edge["data"]["label"]} for edge in edges]
    }
    
    # JSON format (simplified)
    json_format = {
        "graph": {
            "nodes": [node["data"] for node in nodes],
            "edges": [edge["data"] for edge in edges]
        }
    }
    
    return {
        "csv_data": csv_data,
        "graphml_structure": graphml_structure,
        "json_format": json_format,
        "formats_available": ["CSV", "GraphML", "JSON", "Cytoscape"]
    }

@app.get("/visualize", response_class=HTMLResponse, tags=["Visualization"])
async def get_visualization_page():
    """
    Get a standalone visualization page for testing.
    """
    sample_relationships = [
        {"source": "Machine Learning", "target": "Neural Networks", "relation": "uses"},
        {"source": "Deep Learning", "target": "Computer Vision", "relation": "enables"},
        {"source": "Neural Networks", "target": "Pattern Recognition", "relation": "performs"},
        {"source": "Computer Vision", "target": "Image Processing", "relation": "requires"},
        {"source": "Machine Learning", "target": "Data Analysis", "relation": "enables"}
    ]
    
    # Create a simple HTML visualization page
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Knowledge Graph Visualization</title>
        <script src="https://unpkg.com/cytoscape@3.21.0/dist/cytoscape.min.js"></script>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; }}
            #cy {{ width: 100%; height: 600px; border: 1px solid #ccc; }}
            .info {{ margin-bottom: 20px; padding: 10px; background: #f5f5f5; border-radius: 5px; }}
        </style>
    </head>
    <body>
        <div class="info">
            <h1>Sample Knowledge Graph Visualization</h1>
            <p>This is a sample visualization showing relationships between concepts.</p>
            <p>Use the /upload or /upload_enhanced endpoints to generate graphs from your PDF documents.</p>
        </div>
        <div id="cy"></div>
        
        <script>
            // Sample data
            const relationships = {sample_relationships};
            
            // Convert to Cytoscape format
            const nodes = new Set();
            const elements = [];
            
            relationships.forEach(rel => {{
                nodes.add(rel.source);
                nodes.add(rel.target);
            }});
            
            // Add nodes
            nodes.forEach(node => {{
                elements.push({{
                    data: {{ id: node, label: node }}
                }});
            }});
            
            // Add edges
            relationships.forEach((rel, index) => {{
                elements.push({{
                    data: {{
                        id: `edge-${{index}}`,
                        source: rel.source,
                        target: rel.target,
                        label: rel.relation
                    }}
                }});
            }});
            
            // Initialize Cytoscape
            const cy = cytoscape({{
                container: document.getElementById('cy'),
                elements: elements,
                style: [
                    {{
                        selector: 'node',
                        style: {{
                            'background-color': '#666',
                            'label': 'data(label)',
                            'text-valign': 'center',
                            'text-halign': 'center',
                            'color': '#fff',
                            'text-outline-width': 2,
                            'text-outline-color': '#666'
                        }}
                    }},
                    {{
                        selector: 'edge',
                        style: {{
                            'width': 3,
                            'line-color': '#ccc',
                            'target-arrow-color': '#ccc',
                            'target-arrow-shape': 'triangle',
                            'curve-style': 'bezier',
                            'label': 'data(label)',
                            'text-rotation': 'autorotate',
                            'font-size': '12px'
                        }}
                    }}
                ],
                layout: {{
                    name: 'cose',
                    idealEdgeLength: 100,
                    nodeOverlap: 20,
                    refresh: 20,
                    fit: true,
                    padding: 30,
                    randomize: false,
                    componentSpacing: 100,
                    nodeRepulsion: 400000,
                    edgeElasticity: 100,
                    nestingFactor: 5,
                    gravity: 80,
                    numIter: 1000,
                    initialTemp: 200,
                    coolingFactor: 0.95,
                    minTemp: 1.0
                }}
            }});
        </script>
    </body>
    </html>
    """
    
    return HTMLResponse(content=html_content)


@app.get("/query", response_model=QueryResponse, tags=["Search"])
async def search_by_node(
    node: str = Query(..., description="Concept/node to search for"),
    domain: str = Query(..., description="Domain/field to search within"),
    limit: int = Query(10, ge=1, le=50, description="Maximum number of papers to return")
):
    """
    Search for related papers by node and domain.
    
    - **node**: The concept or entity to search for
    - **domain**: The academic domain or field
    - **limit**: Maximum number of papers to return (1-50)
    """
    try:
        if not node.strip() or not domain.strip():
            raise HTTPException(
                status_code=400,
                detail="Both node and domain parameters are required"
            )
        
        logger.info(f"Searching for papers: node='{node}', domain='{domain}', limit={limit}")
        
        # Call the function with proper parameters
        papers = await asyncio.to_thread(
            get_related_papers_by_domain, node.strip(), domain.strip()
        )
        
        # Limit results if we got more than requested
        if len(papers) > limit:
            papers = papers[:limit]
        
        return QueryResponse(results=papers)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Query failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Query failed: {str(e)}"
        )


@app.get("/author", response_model=QueryResponse, tags=["Search"])
async def get_author_papers(
    name: str = Query(..., description="Author name to search for")
):
    """
    Get papers by author name.
    
    - **name**: The author's name to search for
    """
    try:
        if not name.strip():
            raise HTTPException(
                status_code=400,
                detail="Author name is required"
            )
        
        logger.info(f"Searching for author papers: '{name}'")
        
        papers = await asyncio.to_thread(get_papers_by_author, name.strip())
        
        return QueryResponse(results=papers)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Author query failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Author query failed: {str(e)}"
        )

@app.get("/graph_by_paper", tags=["Knowledge Graph"])
async def graph_by_paper(
    paper_id: str = Query(..., description="Paper ID to generate graph for")
):
    """
    Generate knowledge graph for a specific paper.
    
    - **paper_id**: The ID of the paper to process
    
    Note: This endpoint is not yet implemented.
    """
    logger.warning(f"graph_by_paper called with paper_id: {paper_id} (not implemented)")
    
    raise HTTPException(
        status_code=501,
        detail="This endpoint is not yet implemented. Please use the /upload or /upload_enhanced endpoints to process PDF files."
    )

@app.get("/stats", tags=["Analytics"])
async def get_processing_stats():
    """Get processing statistics and usage metrics."""
    try:
        # Count files in upload directory
        uploaded_files = 0
        total_size = 0
        
        if UPLOAD_DIR.exists():
            for file_path in UPLOAD_DIR.iterdir():
                if file_path.is_file():
                    uploaded_files += 1
                    total_size += file_path.stat().st_size
        
        # Get system uptime (approximate)
        import time
        current_time = time.time()
        
        return {
            "processing_stats": {
                "files_in_upload_dir": uploaded_files,
                "total_upload_size_mb": round(total_size / (1024 * 1024), 2),
                "average_file_size_mb": round((total_size / uploaded_files) / (1024 * 1024), 2) if uploaded_files > 0 else 0
            },
            "system_info": {
                "current_timestamp": current_time,
                "upload_directory_size": f"{uploaded_files} files",
                "api_version": "2.0.0"
            },
            "capabilities": {
                "max_concurrent_uploads": 5,  # Could be configurable
                "supported_languages": ["English"],  # Expand as needed
                "extraction_methods": ["LLM (Ollama)", "Rule-based fallback", "NLP patterns"]
            }
        }
        
    except Exception as e:
        logger.error(f"Stats retrieval failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve stats: {str(e)}"
        )

# Add endpoint for cleaning up old files
@app.post("/cleanup", tags=["Maintenance"])
async def cleanup_old_files(
    max_age_hours: int = Query(24, description="Maximum age of files to keep (hours)"),
    dry_run: bool = Query(True, description="If true, only report what would be deleted")
):
    """
    Clean up old uploaded files.
    
    - **max_age_hours**: Files older than this will be deleted
    - **dry_run**: If true, only shows what would be deleted without actually deleting
    """
    try:
        import time
        from datetime import datetime, timedelta
        
        if not UPLOAD_DIR.exists():
            return {"message": "Upload directory does not exist", "files_processed": 0}
        
        cutoff_time = time.time() - (max_age_hours * 3600)
        files_to_delete = []
        total_size = 0
        
        # Find old files
        for file_path in UPLOAD_DIR.iterdir():
            if file_path.is_file():
                file_mtime = file_path.stat().st_mtime
                if file_mtime < cutoff_time:
                    file_size = file_path.stat().st_size
                    files_to_delete.append({
                        "filename": file_path.name,
                        "size_mb": round(file_size / (1024 * 1024), 2),
                        "age_hours": round((time.time() - file_mtime) / 3600, 1),
                        "path": str(file_path)
                    })
                    total_size += file_size
        
        # Delete files if not dry run
        deleted_count = 0
        if not dry_run:
            for file_info in files_to_delete:
                try:
                    Path(file_info["path"]).unlink()
                    deleted_count += 1
                except Exception as e:
                    logger.error(f"Failed to delete {file_info['filename']}: {e}")
        
        return {
            "dry_run": dry_run,
            "max_age_hours": max_age_hours,
            "files_found": len(files_to_delete),
            "files_deleted": deleted_count if not dry_run else 0,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "files": files_to_delete[:20] if dry_run else [],  # Limit response size
            "message": f"{'Would delete' if dry_run else 'Deleted'} {len(files_to_delete)} files"
        }
        
    except Exception as e:
        logger.error(f"Cleanup failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Cleanup failed: {str(e)}"
        )

# Add configuration endpoint
@app.get("/config", tags=["Configuration"])
async def get_configuration():
    """Get current API configuration."""
    return {
        "file_processing": {
            "max_file_size_mb": MAX_FILE_SIZE // (1024 * 1024),
            "allowed_extensions": list(ALLOWED_EXTENSIONS),
            "upload_directory": str(UPLOAD_DIR),
            "text_preview_length": TEXT_PREVIEW_LENGTH
        },
        "extraction": {
            "default_chunk_size": 1500,
            "default_chunk_overlap": 150,
            "max_relationships_per_chunk": 15,
            "ollama_timeout_seconds": 45
        },
        "api": {
            "cors_origins": ["*"],  # Should be restricted in production
            "max_batch_files": 10,
            "supported_export_formats": ["json", "csv", "graphml", "gexf", "cytoscape"]
        },
        "features": {
            "enhanced_processing": True,
            "batch_processing": True,
            "graph_analysis": True,
            "graph_merging": True,
            "multiple_export_formats": True,
            "semantic_scholar_integration": True
        }
    }


@app.get("/docs", response_class=HTMLResponse, tags=["Documentation"])
async def get_api_docs():
    """Generate custom API documentation."""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Knowledge Graph API Documentation</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; }
            .endpoint { background: #f5f5f5; padding: 15px; margin: 10px 0; border-radius: 5px; }
            .method { color: #fff; padding: 5px 10px; border-radius: 3px; font-weight: bold; }
            .post { background: #49cc90; }
            .get { background: #61affe; }
            code { background: #f0f0f0; padding: 2px 5px; border-radius: 3px; }
        </style>
    </head>
    <body>
        <h1>Knowledge Graph API Documentation</h1>
        
        <h2>Overview</h2>
        <p>This API extracts knowledge graphs from PDF documents using advanced NLP techniques.</p>
        
        <h2>Endpoints</h2>
        
        <div class="endpoint">
            <h3><span class="method post">POST</span> /upload_enhanced</h3>
            <p><strong>Enhanced PDF processing with configurable options</strong></p>
            <p><strong>Parameters:</strong></p>
            <ul>
                <li><code>file</code> - PDF file to process (required)</li>
                <li><code>chunk_size</code> - Text chunk size (500-3000, default: 1500)</li>
                <li><code>chunk_overlap</code> - Chunk overlap (0-500, default: 150)</li>
                <li><code>max_relationships</code> - Max relationships (5-50, default: 15)</li>
                <li><code>enable_debug</code> - Include debug info (default: false)</li>
                <li><code>export_formats</code> - Include export data (default: false)</li>
            </ul>
        </div>
        
        <div class="endpoint">
            <h3><span class="method post">POST</span> /upload</h3>
            <p><strong>Basic PDF processing (legacy)</strong></p>
            <p><strong>Parameters:</strong></p>
            <ul>
                <li><code>file</code> - PDF file to process (required)</li>
            </ul>
        </div>
        
        <div class="endpoint">
            <h3><span class="method get">GET</span> /query</h3>
            <p><strong>Search for related papers</strong></p>
            <p><strong>Parameters:</strong></p>
            <ul>
                <li><code>node</code> - Concept to search for (required)</li>
                <li><code>domain</code> - Academic domain (required)</li>
            </ul>
        </div>
        
        <div class="endpoint">
            <h3><span class="method get">GET</span> /author</h3>
            <p><strong>Get papers by author</strong></p>
            <p><strong>Parameters:</strong></p>
            <ul>
                <li><code>name</code> - Author name (required)</li>
            </ul>
        </div>
        
        <h2>Response Formats</h2>
        <p>All responses include Cytoscape-compatible graph data with nodes and edges.</p>
        
        <h2>File Limits</h2>
        <ul>
            <li>Maximum file size: 50MB</li>
            <li>Supported formats: PDF only</li>
            <li>Minimum text length: 100 characters</li>
        </ul>
        
        <p><a href="/docs">Interactive API Documentation (Swagger)</a></p>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

# Error handlers
@app.exception_handler(HTTPException)
async def enhanced_http_exception_handler(request, exc):
    """Enhanced HTTP exception handler with detailed error info."""
    error_id = str(uuid.uuid4())[:8]
    
    logger.error(f"HTTP Exception [{error_id}]: {exc.status_code} - {exc.detail}")
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": True,
            "error_id": error_id,
            "status_code": exc.status_code,
            "detail": exc.detail,
            "timestamp": time.time(),
            "path": str(request.url.path) if hasattr(request, 'url') else None
        }
    )

@app.exception_handler(Exception)
async def enhanced_general_exception_handler(request, exc):
    """Enhanced general exception handler with tracking."""
    error_id = str(uuid.uuid4())[:8]
    
    logger.error(f"Unhandled exception [{error_id}] on {request.url}: {exc}")
    logger.error(f"Traceback [{error_id}]: {traceback.format_exc()}")
    
    return JSONResponse(
        status_code=500,
        content={
            "error": True,
            "error_id": error_id,
            "status_code": 500,
            "detail": "Internal server error",
            "message": "An unexpected error occurred. Please try again or contact support.",
            "timestamp": time.time(),
            "path": str(request.url.path) if hasattr(request, 'url') else None
        }
    )

# Add startup time tracking
start_time = time.time()

@app.post("/search_papers_by_node", response_model=NodeInteractionResponse, tags=["Search"])
async def search_papers_by_node(
    request: DomainSearchRequest
):
    """
    Search for papers related to a specific node/concept in a domain.
    
    - **node**: The concept or entity to search for
    - **domain**: The academic domain or field
    """
    try:
        node = request.node.strip()
        domain = request.domain.strip()
        
        if not node or not domain:
            raise HTTPException(
                status_code=400,
                detail="Both node and domain are required"
            )
        
        logger.info(f"Searching for papers: node='{node}', domain='{domain}'")
        
        papers = await asyncio.to_thread(
            get_related_papers_by_domain, 
            node, 
            domain,
            limit=20  # Get more papers for better selection
        )
        
        # Enhance paper data with additional info
        enhanced_papers = []
        for paper in papers:
            enhanced_paper = {
                **paper,
                "relevance_score": calculate_relevance_score(paper, node),
                "can_extract_graph": check_if_extractable(paper),
                "preview_text": paper.get("abstract", "")[:200] + "..." if paper.get("abstract") else ""
            }
            enhanced_papers.append(enhanced_paper)
        
        # Sort by relevance score
        enhanced_papers.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)
        
        return NodeInteractionResponse(
            success=True,
            node=node,
            domain=domain,
            papers=enhanced_papers,
            total_found=len(enhanced_papers)
        )
        
    except Exception as e:
        logger.error(f"Error searching papers for node: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to search papers: {str(e)}"
        )
@app.post("/generate_paper_graph", response_model=PaperGraphResponse, tags=["Node Interaction"])
async def generate_paper_graph(
    background_tasks: BackgroundTasks,
    request: PaperGraphRequest
):
    """
    Generate knowledge graph from a research paper.
    
    - **paper_id**: The Semantic Scholar paper ID
    - **paper_url**: Optional direct URL to paper PDF
    """
    try:
        paper_id = request.paper_id.strip() if request.paper_id else ""
        paper_url = request.paper_url.strip() if request.paper_url else ""
        
        if not paper_id:
            raise HTTPException(
                status_code=400,
                detail="Paper ID is required"
            )
        
        logger.info(f"Generating graph for paper: {paper_id}")
        
        # Get paper details from Semantic Scholar
        from backend.helpers.semantic_scholar import get_paper_details
        paper_info = await asyncio.to_thread(get_paper_details, paper_id)
        
        if not paper_info:
            raise HTTPException(
                status_code=404,
                detail="Paper not found or inaccessible"
            )
        
        # Extract text from paper
        text_content = ""
        
        # Try to get text from abstract first
        if paper_info.get('abstract'):
            text_content = paper_info['abstract']
            logger.info("Using paper abstract for graph generation")
        else:
            # If we have a PDF URL, try to extract from PDF
            pdf_url = paper_url or paper_info.get('pdf_url')
            if pdf_url:
                try:
                    # Download and extract PDF content
                    text_content = await extract_paper_text(paper_info, pdf_url)
                    logger.info("Extracted text from PDF URL")
                except Exception as e:
                    logger.warning(f"Failed to extract from PDF: {e}")
                    raise HTTPException(
                        status_code=422,
                        detail="Could not extract text from paper. Abstract not available and PDF extraction failed."
                    )
            else:
                raise HTTPException(
                    status_code=422,
                    detail="No abstract or PDF available for this paper"
                )
        
        if len(text_content.strip()) < 100:
            raise HTTPException(
                status_code=422,
                detail="Insufficient text content for graph generation"
            )
        
        logger.info(f"Processing text content: {len(text_content)} characters")
        
        # Extract relationships
        raw_relationships = await asyncio.to_thread(
            extract_concepts_with_relationships, text_content
        )
        
        if not isinstance(raw_relationships, list):
            raise ValueError("Relationship extraction failed")
        
        # Validate relationships
        relationships = validate_relationships(raw_relationships)
        
        if not relationships:
            raise HTTPException(
                status_code=422,
                detail="No valid relationships could be extracted from this paper"
            )
        
        # Format for visualization
        elements = format_for_cytoscape(relationships)
        
        # Analyze graph structure - use relationships
        graph_analysis = analyze_graph_structure(relationships)
        
        # Prepare response metadata
        metadata = {
            "paper_id": paper_id,
            "paper_title": paper_info.get('title', ''),
            "paper_authors": paper_info.get('authors', []),
            "paper_year": paper_info.get('year'),
            "paper_venue": paper_info.get('venue', ''),
            "paper_citation_count": paper_info.get('citation_count', 0),
            "text_length": len(text_content),
            "num_relationships": len(relationships),
            "num_nodes": len([e for e in elements if "source" not in e["data"]]),
            "num_edges": len([e for e in elements if "source" in e["data"]]),
            "analysis": graph_analysis,
            "source": "semantic_scholar"
        }
        
        return PaperGraphResponse(
            success=True,
            paper_info=paper_info,
            graph=elements,
            metadata=metadata
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Paper graph generation failed: {e}")
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate graph from paper: {str(e)}"
        )# Helper functions

# Add endpoint to list available papers (for testing)
@app.get("/papers/sample", tags=["Search"])
async def get_sample_papers():
    """
    Get a list of sample papers for testing.
    """
    sample_papers = [
        {
            "paperId": "sample-001",
            "title": "Deep Learning Approaches to Natural Language Processing",
            "abstract": "This paper explores various deep learning techniques applied to natural language processing tasks, including sentiment analysis, machine translation, and text summarization.",
            "authors": [{"name": "Dr. AI Researcher"}],
            "year": 2023,
            "citation_count": 156,
            "can_extract_graph": True
        },
        {
            "paperId": "sample-002", 
            "title": "Graph Neural Networks for Knowledge Representation",
            "abstract": "We present a comprehensive study of graph neural networks and their applications in knowledge representation and reasoning tasks.",
            "authors": [{"name": "Prof. Graph Theory"}],
            "year": 2022,
            "citation_count": 89,
            "can_extract_graph": True
        },
        {
            "paperId": "sample-003",
            "title": "Transformer Architectures in Computer Vision",
            "abstract": "An analysis of how transformer architectures have revolutionized computer vision tasks beyond their original application in natural language processing.",
            "authors": [{"name": "Dr. Vision Expert"}],
            "year": 2023,
            "citation_count": 203,
            "can_extract_graph": True
        }
    ]
    
    return {
        "success": True,
        "papers": sample_papers,
        "total": len(sample_papers)
    }


def calculate_relevance_score(paper: Dict[str, Any], node: str) -> float:
    """Calculate relevance score based on node appearance in paper."""
    score = 0.0
    node_lower = node.lower()
    
    # Check title
    title = paper.get("title", "").lower()
    if node_lower in title:
        score += 3.0
    
    # Check abstract
    abstract = paper.get("abstract", "").lower()
    if node_lower in abstract:
        score += 2.0
    
    # Boost score based on citation count
    citation_count = paper.get("citation_count", 0)
    if citation_count > 100:
        score += 1.0
    elif citation_count > 50:
        score += 0.5
    
    # Boost recent papers
    year = paper.get("year", 0)
    if year and year > 2020:
        score += 0.5
    
    return score

def check_if_extractable(paper: Dict[str, Any]) -> bool:
    """Check if paper has extractable content."""
    # For now, we'll assume papers with abstracts are extractable
    # In a real implementation, you'd check for PDF availability
    return bool(paper.get("abstract") and len(paper.get("abstract", "")) > 100)

async def extract_paper_text(paper_details: Dict[str, Any], paper_url: Optional[str] = None) -> str:
    """Extract text from a research paper."""
    
    # Method 1: Try to download PDF if URL is provided
    if paper_url and paper_url.endswith('.pdf'):
        try:
            text = await download_and_extract_pdf(paper_url)
            if text and len(text.strip()) > 500:
                return text
        except Exception as e:
            logger.warning(f"Failed to extract from PDF URL: {e}")
    
    # Method 2: Use paper URL from Semantic Scholar
    semantic_url = paper_details.get("url")
    if semantic_url and "pdf" in semantic_url.lower():
        try:
            text = await download_and_extract_pdf(semantic_url)
            if text and len(text.strip()) > 500:
                return text
        except Exception as e:
            logger.warning(f"Failed to extract from Semantic Scholar PDF: {e}")
    
    # Method 3: Fallback to abstract and available text
    abstract = paper_details.get("abstract", "")
    title = paper_details.get("title", "")
    
    # Combine available text
    combined_text = f"{title}. {abstract}"
    
    if len(combined_text.strip()) > 100:
        return combined_text
    
    raise ValueError("No extractable text found for this paper")

async def download_and_extract_pdf(url: str) -> str:
    """Download PDF and extract text."""
    temp_file = None
    try:
        # Create temporary file
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
            temp_path = temp_file.name
        
        # Download PDF
        urllib.request.urlretrieve(url, temp_path)
        
        # Extract text using existing function
        text = extract_text_from_pdf(Path(temp_path))
        
        return text
        
    except Exception as e:
        logger.error(f"Error downloading/extracting PDF: {e}")
        raise
    finally:
        # Clean up temp file
        if temp_file and os.path.exists(temp_path):
            try:
                os.unlink(temp_path)
            except:
                pass

def analyze_graph_structure_from_elements(elements: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analyze the structure of the knowledge graph from Cytoscape elements."""
    nodes = [e for e in elements if "source" not in e["data"]]
    edges = [e for e in elements if "source" in e["data"]]
    
    # Basic statistics
    num_nodes = len(nodes)
    num_edges = len(edges)
    
    # Calculate node degrees
    node_degrees = {}
    for edge in edges:
        source = edge["data"]["source"]
        target = edge["data"]["target"]
        node_degrees[source] = node_degrees.get(source, 0) + 1
        node_degrees[target] = node_degrees.get(target, 0) + 1
    
    # Find central nodes
    central_nodes = sorted(node_degrees.items(), key=lambda x: x[1], reverse=True)[:5]
    
    # Calculate density
    max_edges = num_nodes * (num_nodes - 1) / 2 if num_nodes > 1 else 1
    density = num_edges / max_edges if max_edges > 0 else 0
    
    return {
        "num_nodes": num_nodes,
        "num_edges": num_edges,
        "density": round(density, 3),
        "avg_degree": round(sum(node_degrees.values()) / len(node_degrees), 2) if node_degrees else 0,
        "central_nodes": central_nodes,
        "max_degree": max(node_degrees.values()) if node_degrees else 0
    }
# Add chunk_text function that was referenced but missing
def chunk_text(text: str, chunk_size: int, chunk_overlap: int) -> List[str]:
    """Split text into overlapping chunks."""
    if len(text) <= chunk_size:
        return [text]
    
    chunks = []
    start = 0
    
    while start < len(text):
        end = start + chunk_size
        
        # Try to break at sentence boundary
        if end < len(text):
            # Look for sentence ending within the last 100 characters
            last_period = text.rfind('.', start, end)
            if last_period > start + chunk_size - 100:
                end = last_period + 1
        
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        
        start = end - chunk_overlap
        
        if start >= len(text):
            break
    
    return chunks

if __name__ == "__main__":
    import uvicorn
    
    logger.info("Starting Knowledge Graph API server...")
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
@app.get("/health", tags=["Health"])
async def health_check():
    """Comprehensive health check endpoint."""
    try:
        health_status = {
            "status": "healthy",
            "timestamp": time.time(),
            "version": "2.0.0",
            "components": {
                "file_system": "ok",
                "extraction_engine": "unknown",
                "semantic_scholar": "unknown"
            }
        }
        
        # Check upload directory
        try:
            if UPLOAD_DIR.exists() and UPLOAD_DIR.is_dir():
                health_status["components"]["file_system"] = "ok"
            else:
                health_status["components"]["file_system"] = "error"
                health_status["status"] = "degraded"
        except Exception:
            health_status["components"]["file_system"] = "error"
            health_status["status"] = "degraded"
        
        # Test extraction engine with simple text
        try:
            test_text = "Machine learning is a subset of artificial intelligence."
            test_result = await asyncio.wait_for(
                asyncio.to_thread(extract_concepts_with_relationships, test_text),
                timeout=10.0
            )
            if isinstance(test_result, list):
                health_status["components"]["extraction_engine"] = "ok"
            else:
                health_status["components"]["extraction_engine"] = "warning"
        except asyncio.TimeoutError:
            health_status["components"]["extraction_engine"] = "timeout"
            health_status["status"] = "degraded"
        except Exception as e:
            health_status["components"]["extraction_engine"] = f"error: {str(e)}"
            health_status["status"] = "degraded"
        
        # Test Semantic Scholar API
        try:
            from backend.helpers.semantic_scholar import get_related_papers_by_domain
            test_papers = await asyncio.wait_for(
                asyncio.to_thread(get_related_papers_by_domain, "test", "computer science"),
                timeout=5.0
            )
            if isinstance(test_papers, list):
                health_status["components"]["semantic_scholar"] = "ok"
            else:
                health_status["components"]["semantic_scholar"] = "warning"
        except asyncio.TimeoutError:
            health_status["components"]["semantic_scholar"] = "timeout"
        except Exception as e:
            health_status["components"]["semantic_scholar"] = f"error: {str(e)}"
        
        return health_status
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "error",
            "timestamp": time.time(),
            "error": str(e)
        }

@app.get("/paper/{paper_id}/graph", tags=["Knowledge Graph"])
@app.get("/paper/{paper_id}/graph", tags=["Knowledge Graph"])
async def get_paper_graph_by_id(
    paper_id: str,
    background_tasks: BackgroundTasks
):
    """
    Generate knowledge graph for a paper by its ID (GET request).
    """
    try:
        # Create a request object for the existing function
        request = PaperGraphRequest(paper_id=paper_id, paper_url=None)
        
        # Call the existing function
        result = await generate_paper_graph(background_tasks, request)
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to generate graph for paper {paper_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate graph: {str(e)}"
        )