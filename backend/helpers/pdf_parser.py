"""
Enhanced PDF parsing and concept extraction module.
Combines multiple extraction methods for optimal results.
"""
import sys
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
import logging
import time

# Add parent directory to path to import extractor
current_dir = Path(__file__).parent
backend_dir = current_dir.parent
sys.path.append(str(backend_dir))

try:
    from extractor import extract_concepts_with_relationships
    EXTRACTOR_AVAILABLE = True
except ImportError:
    EXTRACTOR_AVAILABLE = False
    logging.warning("Enhanced extractor not available, using fallback")

# Additional imports for enhanced processing
try:
    import fitz  # PyMuPDF
    HAS_PYMUPDF = True
except ImportError:
    HAS_PYMUPDF = False

try:
    from langchain.document_loaders import PyPDFLoader
    from langchain.text_splitter import RecursiveCharacterTextSplitter
    HAS_LANGCHAIN = True
except ImportError:
    HAS_LANGCHAIN = False

logger = logging.getLogger(__name__)

class EnhancedPDFParser:
    """Enhanced PDF parser with multiple extraction methods."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.chunk_size = self.config.get('chunk_size', 1500)
        self.chunk_overlap = self.config.get('chunk_overlap', 150)
        self.min_text_length = self.config.get('min_text_length', 100)
        
    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """
        Extract text from PDF using the best available method.
        """
        pdf_path = Path(pdf_path)
        
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        
        # Try PyMuPDF first (best quality)
        if HAS_PYMUPDF:
            try:
                return self._extract_with_pymupdf(pdf_path)
            except Exception as e:
                logger.warning(f"PyMuPDF extraction failed: {e}")
        
        # Try LangChain PyPDFLoader
        if HAS_LANGCHAIN:
            try:
                return self._extract_with_langchain(pdf_path)
            except Exception as e:
                logger.warning(f"LangChain extraction failed: {e}")
        
        # Fallback to basic extraction
        logger.warning("Using basic PDF extraction fallback")
        return self._extract_basic_fallback(pdf_path)
    
    def _extract_with_pymupdf(self, pdf_path: Path) -> str:
        """Extract text using PyMuPDF with enhanced processing."""
        logger.info("Extracting text with PyMuPDF...")
        
        with open(pdf_path, "rb") as f:
            doc = fitz.open(stream=f.read(), filetype="pdf")
        
        text_parts = []
        metadata = {
            'total_pages': len(doc),
            'pages_processed': 0,
            'pages_with_text': 0
        }
        
        for page_num in range(len(doc)):
            try:
                page = doc[page_num]
                
                # Extract text with formatting preservation
                page_text = page.get_text("text")
                
                # Clean and validate page text
                cleaned_text = self._clean_page_text(page_text)
                
                if len(cleaned_text.strip()) > self.min_text_length:
                    text_parts.append(cleaned_text)
                    metadata['pages_with_text'] += 1
                
                metadata['pages_processed'] += 1
                
            except Exception as e:
                logger.warning(f"Error extracting text from page {page_num}: {e}")
                continue
        
        doc.close()
        
        if not text_parts:
            raise ValueError("No readable text found in the PDF")
        
        full_text = "\n\n".join(text_parts)
        logger.info(f"Extracted {len(full_text)} characters from {metadata['pages_with_text']}/{metadata['total_pages']} pages")
        
        return full_text
    
    def _extract_with_langchain(self, pdf_path: Path) -> str:
        """Extract text using LangChain PyPDFLoader."""
        logger.info("Extracting text with LangChain...")
        
        loader = PyPDFLoader(str(pdf_path))
        pages = loader.load()
        
        if not pages:
            raise ValueError("No pages loaded from PDF")
        
        # Combine all page content
        text_parts = []
        for page in pages:
            page_text = page.page_content
            cleaned_text = self._clean_page_text(page_text)
            
            if len(cleaned_text.strip()) > self.min_text_length:
                text_parts.append(cleaned_text)
        
        if not text_parts:
            raise ValueError("No readable text found in the PDF")
        
        full_text = "\n\n".join(text_parts)
        logger.info(f"Extracted {len(full_text)} characters from {len(pages)} pages")
        
        return full_text
    
    def _extract_basic_fallback(self, pdf_path: Path) -> str:
        """Basic fallback extraction method."""
        logger.warning("Using basic fallback - limited functionality")
        
        # This is a very basic fallback - in practice, you might want to
        # use another PDF library like pdfplumber or pypdf2
        try:
            with open(pdf_path, 'rb') as f:
                # This is just a placeholder - implement actual basic extraction
                content = f.read()
                # Extract any readable text (very basic)
                text = str(content, errors='ignore')
                return self._clean_page_text(text)
        except Exception as e:
            logger.error(f"Basic extraction failed: {e}")
            raise ValueError("Failed to extract text from PDF")
    
    def _clean_page_text(self, text: str) -> str:
        """Clean and normalize page text."""
        if not text:
            return ""
        
        # Remove excessive whitespace
        import re
        text = re.sub(r'\s+', ' ', text.strip())
        
        # Remove common PDF artifacts
        text = re.sub(r'\x0c', ' ', text)  # Form feed characters
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\xff]', ' ', text)  # Control characters
        
        # Remove page numbers and headers/footers (basic heuristics)
        lines = text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            line = line.strip()
            # Skip very short lines that are likely page numbers or artifacts
            if len(line) < 3:
                continue
            # Skip lines that are just numbers (page numbers)
            if line.isdigit():
                continue
            # Skip common header/footer patterns
            if re.match(r'^(page \d+|chapter \d+|\d+\s*$)', line.lower()):
                continue
            
            cleaned_lines.append(line)
        
        return ' '.join(cleaned_lines)

def extract_concepts_with_relationships_safe(text: str) -> List[Dict[str, str]]:
    """
    A safer wrapper around extract_concepts_with_relationships that handles errors gracefully.
    """
    try:
        # Try to extract relationships
        relationships = extract_concepts_with_relationships(text)
        
        # Validate the output format
        if not isinstance(relationships, list):
            logger.error(f"Extractor returned non-list: {type(relationships)}")
            return []
        
        # Ensure each relationship has the required fields
        valid_relationships = []
        for rel in relationships:
            if isinstance(rel, dict) and all(k in rel for k in ["source", "target", "relation"]):
                valid_relationships.append(rel)
            else:
                logger.warning(f"Invalid relationship format: {rel}")
        
        return valid_relationships
        
    except Exception as e:
        logger.error(f"Error in relationship extraction: {e}")
        return []

def extract_concepts_with_relationships(text: str) -> List[Dict[str, str]]:
    """
    Main function for extracting concepts and relationships from text.
    Uses the enhanced extractor if available, otherwise falls back to basic extraction.
    """
    if EXTRACTOR_AVAILABLE:
        # Use the enhanced extractor from extractor.py
        from extractor import extract_concepts_with_relationships as enhanced_extract
        return enhanced_extract(text)
    else:
        # Use the fallback implementation
        return _fallback_extract_concepts_with_relationships(text)

def _fallback_extract_concepts_with_relationships(text: str) -> List[Dict[str, str]]:
    """
    Fallback implementation when the enhanced extractor is not available.
    """
    import subprocess
    import json
    import re
    import logging
    
    logger = logging.getLogger(__name__)
    
    # Configuration
    MAX_TEXT_LENGTH = 1500
    OLLAMA_TIMEOUT = 30
    MAX_RELATIONSHIPS = 15
    
    def preprocess_text(text: str) -> str:
        """Clean and preprocess text."""
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text.strip())
        
        # Remove citations and references
        text = re.sub(r'\[\d+\]', '', text)
        text = re.sub(r'\([^)]*\d{4}[^)]*\)', '', text)
        
        # Remove figure/table references
        text = re.sub(r'\b(Figure|Table|Fig\.|Tab\.)\s+\d+[^\w]*', '', text)
        
        # Focus on meaningful sentences
        sentences = [s.strip() for s in text.split('.') if len(s.strip()) > 30]
        
        # Filter for technical content
        technical_sentences = []
        technical_terms = ['algorithm', 'method', 'approach', 'system', 'model', 'technique', 'analysis', 'framework']
        
        for sentence in sentences:
            if any(term in sentence.lower() for term in technical_terms):
                technical_sentences.append(sentence)
            if len(technical_sentences) >= 10:
                break
        
        return '. '.join(technical_sentences) if technical_sentences else '. '.join(sentences[:5])
    
    def extract_with_ollama(text: str) -> List[Dict[str, str]]:
        """Extract using Ollama with improved prompting."""
        processed_text = preprocess_text(text)
        
        prompt = f"""
Extract key concepts and their relationships from this text. Focus on technical terms and their interactions.

Format as JSON array:
[
  {{"source": "ConceptA", "relation": "relationship_type", "target": "ConceptB"}},
  ...
]

Use specific relationships: uses, implements, enables, requires, improves, analyzes, generates

Text: {processed_text[:MAX_TEXT_LENGTH]}

JSON output:
"""
        
        try:
            models = ['mistral:7b', 'mistral', 'llama2:7b', 'llama2']
            
            for model in models:
                try:
                    process = subprocess.Popen(
                        ['ollama', 'run', model],
                        stdin=subprocess.PIPE,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True
                    )
                    
                    stdout, stderr = process.communicate(input=prompt, timeout=OLLAMA_TIMEOUT)
                    
                    if process.returncode == 0 and stdout.strip():
                        return parse_ollama_output(stdout)
                    
                except subprocess.TimeoutExpired:
                    process.kill()
                    continue
                except Exception:
                    continue
            
            return []
            
        except Exception as e:
            logger.error(f"Ollama extraction failed: {e}")
            return []
    
    def parse_ollama_output(output: str) -> List[Dict[str, str]]:
        """Parse Ollama output to extract relationships."""
        relationships = []
        
        # Try to extract JSON array
        json_match = re.search(r'\[\s*\{.*?\}\s*\]', output, re.DOTALL)
        if json_match:
            try:
                data = json.loads(json_match.group())
                if isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict) and all(k in item for k in ['source', 'target', 'relation']):
                            relationships.append({
                                'source': str(item['source']).strip().title(),
                                'target': str(item['target']).strip().title(),
                                'relation': str(item['relation']).strip().lower()
                            })
            except json.JSONDecodeError:
                pass
        
        # Fallback: extract individual JSON objects
        if not relationships:
            obj_pattern = r'\{[^{}]*"source"[^{}]*"target"[^{}]*\}'
            matches = re.findall(obj_pattern, output)
            
            for match in matches:
                try:
                    obj = json.loads(match)
                    if all(k in obj for k in ['source', 'target']):
                        relationships.append({
                            'source': str(obj['source']).strip().title(),
                            'target': str(obj['target']).strip().title(),
                            'relation': str(obj.get('relation', 'relates_to')).strip().lower()
                        })
                except json.JSONDecodeError:
                    continue
        
        return filter_relationships(relationships)
    
    def filter_relationships(relationships: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """Filter relationships for quality."""
        if not relationships:
            return []
        
        GENERIC_TERMS = {
            'data', 'method', 'result', 'study', 'research', 'analysis', 
            'approach', 'technique', 'process', 'system', 'framework',
            'paper', 'work', 'information', 'concept', 'element'
        }
        
        filtered = []
        seen_pairs = set()
        
        for rel in relationships:
            source = rel.get('source', '').strip()
            target = rel.get('target', '').strip()
            relation = rel.get('relation', '').strip()
            
            # Basic validation
            if not all([source, target, relation]) or len(source) < 3 or len(target) < 3:
                continue
            
            # Skip generic terms and self-references
            if (source.lower() in GENERIC_TERMS or target.lower() in GENERIC_TERMS or
                source.lower() == target.lower()):
                continue
            
            # Deduplication
            pair = tuple(sorted([source.lower(), target.lower()]))
            if pair in seen_pairs:
                continue
            seen_pairs.add(pair)
            
            filtered.append({
                'source': source.title(),
                'target': target.title(),
                'relation': relation.lower()
            })
            
            if len(filtered) >= MAX_RELATIONSHIPS:
                break
        
        return filtered
    
    def extract_with_patterns(text: str) -> List[Dict[str, str]]:
        """Extract relationships using pattern matching."""
        relationships = []
        
        # Technical concept patterns
        concept_pattern = r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2}\b'
        concepts = list(set(re.findall(concept_pattern, text)))[:15]
        
        # Relationship patterns
        relationship_patterns = {
            'uses': [r'(\w+(?:\s+\w+)*)\s+(?:uses|utilizes|employs)\s+(\w+(?:\s+\w+)*)'],
            'enables': [r'(\w+(?:\s+\w+)*)\s+(?:enables|allows|facilitates)\s+(\w+(?:\s+\w+)*)'],
            'improves': [r'(\w+(?:\s+\w+)*)\s+(?:improves|enhances|optimizes)\s+(\w+(?:\s+\w+)*)'],
            'implements': [r'(\w+(?:\s+\w+)*)\s+(?:implements|realizes)\s+(\w+(?:\s+\w+)*)'],
            'requires': [r'(\w+(?:\s+\w+)*)\s+(?:requires|needs)\s+(\w+(?:\s+\w+)*)']
        }
        
        for relation, patterns in relationship_patterns.items():
            for pattern in patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                for match in matches:
                    source, target = match
                    if len(source) > 2 and len(target) > 2 and source.lower() != target.lower():
                        relationships.append({
                            'source': source.strip().title(),
                            'target': target.strip().title(),
                            'relation': relation
                        })
        
        # Co-occurrence relationships
        for i, concept1 in enumerate(concepts):
            for concept2 in concepts[i+1:]:
                if concept1.lower() != concept2.lower():
                    # Check if they appear close to each other
                    if are_concepts_related(concept1, concept2, text):
                        relationships.append({
                            'source': concept1.title(),
                            'target': concept2.title(),
                            'relation': 'related_to'
                        })
        
        return relationships[:MAX_RELATIONSHIPS]
    
    def are_concepts_related(concept1: str, concept2: str, text: str) -> bool:
        """Check if concepts are related in text."""
        text_lower = text.lower()
        pos1 = [m.start() for m in re.finditer(re.escape(concept1.lower()), text_lower)]
        pos2 = [m.start() for m in re.finditer(re.escape(concept2.lower()), text_lower)]
        
        for p1 in pos1:
            for p2 in pos2:
                if abs(p1 - p2) < 200:  # Within 200 characters
                    return True
        return False
    
    # Main extraction logic
    logger.info("Starting fallback concept extraction...")
    
    # Try Ollama first
    ollama_result = extract_with_ollama(text)
    if ollama_result:
        logger.info(f"Ollama extraction: {len(ollama_result)} relationships")
        return ollama_result
    
    # Fallback to pattern-based extraction
    logger.warning("Ollama failed, using pattern-based extraction")
    pattern_result = extract_with_patterns(text)
    logger.info(f"Pattern extraction: {len(pattern_result)} relationships")
    
    return pattern_result

def process_pdf_with_chunks(pdf_path: str, chunk_size: int = 1500, chunk_overlap: int = 150) -> Dict[str, Any]:
    """
    Process PDF with chunking strategy similar to extract_graph.ipynb.
    """
    parser = EnhancedPDFParser({
        'chunk_size': chunk_size,
        'chunk_overlap': chunk_overlap
    })
    
    # Extract full text
    full_text = parser.extract_text_from_pdf(pdf_path)
    
    # Create chunks if LangChain is available
    if HAS_LANGCHAIN:
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            is_separator_regex=False
        )
        
        # Create document-like structure
        from langchain.schema import Document
        doc = Document(page_content=full_text, metadata={'source': pdf_path})
        chunks = splitter.split_documents([doc])
        
        # Process each chunk
        all_relationships = []
        chunk_metadata = []
        
        for i, chunk in enumerate(chunks):
            logger.info(f"Processing chunk {i+1}/{len(chunks)}")
            
            chunk_text = chunk.page_content
            chunk_id = f"chunk_{i}_{hash(chunk_text[:100]) % 10000}"
            
            # Extract relationships from chunk
            chunk_relationships = extract_concepts_with_relationships(chunk_text)
            
            # Add chunk metadata to relationships
            for rel in chunk_relationships:
                rel['chunk_id'] = chunk_id
                rel['chunk_index'] = i
            
            all_relationships.extend(chunk_relationships)
            
            chunk_metadata.append({
                'chunk_id': chunk_id,
                'chunk_index': i,
                'text': chunk_text,
                'length': len(chunk_text),
                'word_count': len(chunk_text.split())
            })
        
        # Apply contextual proximity analysis
        enhanced_relationships = apply_contextual_proximity_analysis(all_relationships, chunk_metadata)
        
        return {
            'relationships': enhanced_relationships,
            'chunks': chunk_metadata,
            'metadata': {
                'total_chunks': len(chunks),
                'total_relationships': len(all_relationships),
                'enhanced_relationships': len(enhanced_relationships),
                'text_length': len(full_text)
            }
        }
    
    else:
        # Simple processing without chunking
        relationships = extract_concepts_with_relationships(full_text)
        
        return {
            'relationships': relationships,
            'chunks': [{'chunk_id': 'single_chunk', 'text': full_text, 'length': len(full_text)}],
            'metadata': {
                'total_chunks': 1,
                'total_relationships': len(relationships),
                'text_length': len(full_text)
            }
        }

def apply_contextual_proximity_analysis(relationships: List[Dict[str, Any]], 
                                      chunk_metadata: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Apply contextual proximity analysis similar to extract_graph.ipynb.
    """
    if not relationships:
        return []
    
    # Create chunk mapping
    chunk_map = {chunk['chunk_id']: chunk for chunk in chunk_metadata}
    
    # Group relationships by chunk
    chunk_relationships = {}
    for rel in relationships:
        chunk_id = rel.get('chunk_id', 'unknown')
        if chunk_id not in chunk_relationships:
            chunk_relationships[chunk_id] = []
        chunk_relationships[chunk_id].append(rel)
    
    # Calculate contextual proximity for each chunk
    enhanced_relationships = []
    
    for chunk_id, chunk_rels in chunk_relationships.items():
        if chunk_id not in chunk_map:
            enhanced_relationships.extend(chunk_rels)
            continue
        
        chunk_text = chunk_map[chunk_id]['text']
        
        # Calculate proximity scores
        for rel in chunk_rels:
            proximity_score = calculate_concept_proximity(
                rel['source'], rel['target'], chunk_text
            )
            rel['proximity_score'] = proximity_score
            rel['chunk_text_length'] = len(chunk_text)
        
        # Filter by proximity threshold
        filtered_rels = [rel for rel in chunk_rels if rel.get('proximity_score', 0) > 0.2]
        enhanced_relationships.extend(filtered_rels)
    
    # Add cross-chunk relationships for concepts that appear in multiple chunks
    cross_chunk_relationships = find_cross_chunk_relationships(relationships, chunk_metadata)
    enhanced_relationships.extend(cross_chunk_relationships)
    
    # Remove duplicates and sort by quality
    final_relationships = deduplicate_and_rank_relationships(enhanced_relationships)
    
    return final_relationships

def calculate_concept_proximity(source: str, target: str, text: str) -> float:
    """Calculate proximity score between concepts in text."""
    import re
    
    text_lower = text.lower()
    source_lower = source.lower()
    target_lower = target.lower()
    
    # Find all positions
    source_positions = [m.start() for m in re.finditer(re.escape(source_lower), text_lower)]
    target_positions = [m.start() for m in re.finditer(re.escape(target_lower), text_lower)]
    
    if not source_positions or not target_positions:
        return 0.0
    
    # Calculate minimum distance
    min_distance = min(abs(s - t) for s in source_positions for t in target_positions)
    
    # Convert to proximity score
    if min_distance < 50:
        return 1.0
    elif min_distance < 100:
        return 0.8
    elif min_distance < 200:
        return 0.6
    elif min_distance < 400:
        return 0.4
    else:
        return 0.2

def find_cross_chunk_relationships(relationships: List[Dict[str, Any]], 
                                 chunk_metadata: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Find relationships between concepts that appear across multiple chunks."""
    # Extract all concepts and their chunk appearances
    concept_chunks = {}
    
    for rel in relationships:
        source = rel['source']
        target = rel['target']
        chunk_id = rel.get('chunk_id', 'unknown')
        
        if source not in concept_chunks:
            concept_chunks[source] = set()
        if target not in concept_chunks:
            concept_chunks[target] = set()
        
        concept_chunks[source].add(chunk_id)
        concept_chunks[target].add(chunk_id)
    
    # Find concepts that appear in multiple chunks
    cross_chunk_concepts = {concept: chunks for concept, chunks in concept_chunks.items() 
                           if len(chunks) > 1}
    
    cross_chunk_relationships = []
    
    # Create relationships between concepts that co-occur across chunks
    processed_pairs = set()
    
    for concept1, chunks1 in cross_chunk_concepts.items():
        for concept2, chunks2 in cross_chunk_concepts.items():
            if concept1 != concept2:
                pair = tuple(sorted([concept1, concept2]))
                if pair in processed_pairs:
                    continue
                processed_pairs.add(pair)
                
                # Check if they share chunks
                shared_chunks = chunks1 & chunks2
                if shared_chunks:
                    cross_chunk_relationships.append({
                        'source': concept1,
                        'target': concept2,
                        'relation': 'contextual_proximity',
                        'shared_chunks': list(shared_chunks),
                        'chunk_count': len(shared_chunks),
                        'proximity_score': min(1.0, len(shared_chunks) / 3),
                        'extraction_method': 'cross_chunk'
                    })
    
    return cross_chunk_relationships

def deduplicate_and_rank_relationships(relationships: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Deduplicate and rank relationships by quality."""
    if not relationships:
        return []
    
    # Group by concept pair
    relationship_groups = {}
    
    for rel in relationships:
        source = rel['source'].lower()
        target = rel['target'].lower()
        pair = tuple(sorted([source, target]))
        
        if pair not in relationship_groups:
            relationship_groups[pair] = []
        relationship_groups[pair].append(rel)
    
    # Select best relationship for each pair
    final_relationships = []
    
    for pair, group in relationship_groups.items():
        if len(group) == 1:
            final_relationships.append(group[0])
        else:
            # Select best relationship based on multiple criteria
            best_rel = max(group, key=lambda r: (
                r.get('proximity_score', 0) * 0.4 +
                r.get('confidence', 0.5) * 0.3 +
                (1.0 if r.get('extraction_method') == 'ollama_enhanced' else 0.5) * 0.2 +
                r.get('chunk_count', 1) * 0.1
            ))
            
            # Merge information from other relationships
            best_rel['alternative_relations'] = list(set(r['relation'] for r in group if r != best_rel))
            best_rel['total_occurrences'] = len(group)
            
            final_relationships.append(best_rel)
    
    # Sort by quality score
    final_relationships.sort(key=lambda r: (
        r.get('proximity_score', 0) * 0.4 +
        r.get('confidence', 0.5) * 0.3 +
        r.get('total_occurrences', 1) * 0.2 +
        (1.0 if r.get('extraction_method') in ['ollama_enhanced', 'ner'] else 0.5) * 0.1
    ), reverse=True)
    
    return final_relationships

def create_knowledge_graph_data(relationships: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Create knowledge graph data structure similar to extract_graph.ipynb output.
    """
    # Extract unique nodes
    nodes = {}
    edges = []
    
    for rel in relationships:
        source = rel['source']
        target = rel['target']
        
        # Add nodes
        if source not in nodes:
            nodes[source] = {
                'id': source,
                'label': source,
                'type': 'concept',
                'degree': 0,
                'importance': rel.get('importance', 3)
            }
        
        if target not in nodes:
            nodes[target] = {
                'id': target,
                'label': target,
                'type': 'concept',
                'degree': 0,
                'importance': rel.get('importance', 3)
            }
        
        # Increment degree
        nodes[source]['degree'] += 1
        nodes[target]['degree'] += 1
        
        # Add edge
        edge = {
            'source': source,
            'target': target,
            'relation': rel['relation'],
            'weight': rel.get('proximity_score', 0.5),
            'confidence': rel.get('confidence', 0.5),
            'extraction_method': rel.get('extraction_method', 'unknown')
        }
        
        # Add additional metadata if available
        if 'chunk_id' in rel:
            edge['chunk_id'] = rel['chunk_id']
        if 'chunk_count' in rel:
            edge['chunk_count'] = rel['chunk_count']
        
        edges.append(edge)
    
    # Convert nodes to list
    node_list = list(nodes.values())
    
    # Calculate node importance based on degree
    max_degree = max(node['degree'] for node in node_list) if node_list else 1
    for node in node_list:
        node['normalized_degree'] = node['degree'] / max_degree
        node['size'] = max(10, min(50, node['degree'] * 5))  # Size for visualization
    
    return {
        'nodes': node_list,
        'edges': edges,
        'metadata': {
            'total_nodes': len(node_list),
            'total_edges': len(edges),
            'max_degree': max_degree,
            'avg_degree': sum(node['degree'] for node in node_list) / len(node_list) if node_list else 0,
            'extraction_methods': list(set(edge['extraction_method'] for edge in edges)),
            'relation_types': list(set(edge['relation'] for edge in edges))
        }
    }

def format_for_cytoscape_enhanced(relationships: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Format relationships for Cytoscape visualization with enhanced features.
    """
    graph_data = create_knowledge_graph_data(relationships)
    elements = []
    
    # Add nodes
    for node in graph_data['nodes']:
        element = {
            'data': {
                'id': node['id'],
                'label': node['label'],
                'type': 'concept',
                'degree': node['degree'],
                'importance': node['importance'],
                'size': node['size']
            },
            'classes': f"degree-{min(5, node['degree'])}"  # CSS class for styling
        }
        elements.append(element)
    
    # Add edges
    for edge in graph_data['edges']:
        element = {
            'data': {
                'id': f"{edge['source']}-{edge['target']}-{edge['relation']}",
                'source': edge['source'],
                'target': edge['target'],
                'label': edge['relation'],
                'weight': edge['weight'],
                'confidence': edge['confidence'],
                'extraction_method': edge['extraction_method'],
                'type': 'relationship'
            },
            'classes': f"method-{edge['extraction_method']} confidence-{int(edge['confidence'] * 10)}"
        }
        
        # Add chunk information if available
        if 'chunk_id' in edge:
            element['data']['chunk_id'] = edge['chunk_id']
        if 'chunk_count' in edge:
            element['data']['chunk_count'] = edge['chunk_count']
        
        elements.append(element)
    
    return elements

def export_to_formats(graph_data: Dict[str, Any], output_dir: str) -> Dict[str, str]:
    """
    Export graph data to multiple formats (CSV, JSON, GraphML).
    """
    import json
    import csv
    from pathlib import Path
    
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    exported_files = {}
    
    # Export to JSON
    json_file = output_path / "knowledge_graph.json"
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(graph_data, f, indent=2, ensure_ascii=False)
    exported_files['json'] = str(json_file)
    
    # Export nodes to CSV
    nodes_csv = output_path / "nodes.csv"
    with open(nodes_csv, 'w', newline='', encoding='utf-8') as f:
        if graph_data['nodes']:
            writer = csv.DictWriter(f, fieldnames=graph_data['nodes'][0].keys())
            writer.writeheader()
            writer.writerows(graph_data['nodes'])
    exported_files['nodes_csv'] = str(nodes_csv)
    
    # Export edges to CSV
    edges_csv = output_path / "edges.csv"
    with open(edges_csv, 'w', newline='', encoding='utf-8') as f:
        if graph_data['edges']:
            writer = csv.DictWriter(f, fieldnames=graph_data['edges'][0].keys())
            writer.writeheader()
            writer.writerows(graph_data['edges'])
    exported_files['edges_csv'] = str(edges_csv)
    
    # Export to GraphML (if networkx is available)
    try:
        import networkx as nx
        
        G = nx.Graph()
        
        # Add nodes
        for node in graph_data['nodes']:
            G.add_node(node['id'], **{k: v for k, v in node.items() if k != 'id'})
        
        # Add edges
        for edge in graph_data['edges']:
            G.add_edge(edge['source'], edge['target'], 
                      **{k: v for k, v in edge.items() if k not in ['source', 'target']})
        
        graphml_file = output_path / "knowledge_graph.graphml"
        nx.write_graphml(G, graphml_file)
        exported_files['graphml'] = str(graphml_file)
        
    except ImportError:
        logger.warning("NetworkX not available, skipping GraphML export")
    
    return exported_files

def analyze_graph_metrics(graph_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyze graph metrics and statistics.
    """
    nodes = graph_data['nodes']
    edges = graph_data['edges']
    
    if not nodes or not edges:
        return {'error': 'Insufficient data for analysis'}
    
    # Basic metrics
    num_nodes = len(nodes)
    num_edges = len(edges)
    density = (2 * num_edges) / (num_nodes * (num_nodes - 1)) if num_nodes > 1 else 0
    
    # Degree statistics
    degrees = [node['degree'] for node in nodes]
    avg_degree = sum(degrees) / len(degrees)
    max_degree = max(degrees)
    min_degree = min(degrees)
    
    # Find most connected nodes
    top_nodes = sorted(nodes, key=lambda x: x['degree'], reverse=True)[:10]
    
    # Relation type distribution
    relation_counts = {}
    for edge in edges:
        relation = edge['relation']
        relation_counts[relation] = relation_counts.get(relation, 0) + 1
    
    # Extraction method distribution
    method_counts = {}
    for edge in edges:
        method = edge['extraction_method']
        method_counts[method] = method_counts.get(method, 0) + 1
    
    # Confidence statistics
    confidences = [edge['confidence'] for edge in edges if 'confidence' in edge]
    avg_confidence = sum(confidences) / len(confidences) if confidences else 0
    
    return {
        'basic_metrics': {
            'num_nodes': num_nodes,
            'num_edges': num_edges,
            'density': density,
            'avg_degree': avg_degree,
            'max_degree': max_degree,
            'min_degree': min_degree
        },
        'top_nodes': [{'name': node['label'], 'degree': node['degree']} for node in top_nodes],
        'relation_distribution': relation_counts,
        'extraction_method_distribution': method_counts,
        'quality_metrics': {
            'avg_confidence': avg_confidence,
            'high_confidence_edges': len([e for e in edges if e.get('confidence', 0) > 0.7]),
            'low_confidence_edges': len([e for e in edges if e.get('confidence', 0) < 0.3])
        }
    }

def generate_graph_summary(graph_data: Dict[str, Any], analysis: Dict[str, Any]) -> str:
    """
    Generate a human-readable summary of the knowledge graph.
    """
    if 'error' in analysis:
        return f"Graph analysis failed: {analysis['error']}"
    
    basic = analysis['basic_metrics']
    top_nodes = analysis['top_nodes']
    relations = analysis['relation_distribution']
    quality = analysis['quality_metrics']
    
    summary = f"""
Knowledge Graph Summary
======================

Graph Structure:
- {basic['num_nodes']} concepts (nodes)
- {basic['num_edges']} relationships (edges)
- Average connections per concept: {basic['avg_degree']:.1f}
- Graph density: {basic['density']:.3f}

Most Connected Concepts:
"""
    
    for i, node in enumerate(top_nodes[:5], 1):
        summary += f"{i}. {node['name']} ({node['degree']} connections)\n"
    
    summary += f"\nRelationship Types:\n"
    for relation, count in sorted(relations.items(), key=lambda x: x[1], reverse=True)[:10]:
        summary += f"- {relation}: {count} occurrences\n"
    
    summary += f"""
Quality Metrics:
- Average confidence: {quality['avg_confidence']:.2f}
- High confidence relationships: {quality['high_confidence_edges']}
- Low confidence relationships: {quality['low_confidence_edges']}

Extraction Methods:
"""
    
    methods = analysis['extraction_method_distribution']
    for method, count in sorted(methods.items(), key=lambda x: x[1], reverse=True):
        summary += f"- {method}: {count} relationships\n"
    
    return summary

# Main processing function that ties everything together
def process_pdf_complete(pdf_path: str, output_dir: Optional[str] = None, 
                        config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Complete PDF processing pipeline with all enhancements.
    
    Args:
        pdf_path: Path to the PDF file
        output_dir: Directory to save outputs (optional)
        config: Configuration dictionary (optional)
    
    Returns:
        Dictionary containing all results and metadata
    """
    start_time = time.time()
    
    try:
        logger.info(f"Starting complete PDF processing: {pdf_path}")
        
        # Process PDF with chunking
        result = process_pdf_with_chunks(
            pdf_path, 
            chunk_size=config.get('chunk_size', 1500) if config else 1500,
            chunk_overlap=config.get('chunk_overlap', 150) if config else 150
        )
        
        relationships = result['relationships']
        chunks = result['chunks']
        metadata = result['metadata']
        
        # Create graph data structure
        graph_data = create_knowledge_graph_data(relationships)
        
        # Format for Cytoscape
        cytoscape_elements = format_for_cytoscape_enhanced(relationships)
        
        # Analyze graph
        analysis = analyze_graph_metrics(graph_data)
        
        # Generate summary
        summary = generate_graph_summary(graph_data, analysis)
        
        # Export to files if output directory specified
        exported_files = {}
        if output_dir:
            exported_files = export_to_formats(graph_data, output_dir)
            
            # Save summary
            summary_file = Path(output_dir) / "summary.txt"
            with open(summary_file, 'w', encoding='utf-8') as f:
                f.write(summary)
            exported_files['summary'] = str(summary_file)
        
        processing_time = time.time() - start_time
        
        # Compile final result
        final_result = {
            'success': True,
            'graph_data': graph_data,
            'cytoscape_elements': cytoscape_elements,
            'relationships': relationships,
            'chunks': chunks,
            'analysis': analysis,
            'summary': summary,
            'metadata': {
                **metadata,
                'processing_time': processing_time,
                'pdf_path': pdf_path,
                'config': config or {}
            },
            'exported_files': exported_files
        }
        
        logger.info(f"PDF processing completed successfully in {processing_time:.2f} seconds")
        logger.info(f"Extracted {len(relationships)} relationships from {metadata['total_chunks']} chunks")
        
        return final_result
        
    except Exception as e:
        logger.error(f"PDF processing failed: {e}")
        import traceback
        traceback.print_exc()
        
        return {
            'success': False,
            'error': str(e),
            'metadata': {
                'processing_time': time.time() - start_time,
                'pdf_path': pdf_path
            }
        }

# Convenience function for simple usage
def extract_knowledge_graph_from_pdf(pdf_path: str) -> List[Dict[str, Any]]:
    """
    Simple function to extract knowledge graph from PDF.
    Returns list of relationships in the format expected by the FastAPI app.
    """
    try:
        parser = EnhancedPDFParser()
        text = parser.extract_text_from_pdf(pdf_path)
        relationships = extract_concepts_with_relationships(text)
        
        # Convert to the format expected by the main app
        formatted_relationships = []
        for rel in relationships:
            formatted_rel = {
                'source': rel['source'],
                'target': rel['target'],
                'relation': rel['relation']
            }
            formatted_relationships.append(formatted_rel)
        
        return formatted_relationships
        
    except Exception as e:
        logger.error(f"Simple extraction failed: {e}")
        return []

# For backward compatibility with the existing app.py
def extract_concepts_with_relationships_simple(text: str) -> List[Dict[str, str]]:
    """
    Backward compatible function for the existing FastAPI app.
    """
    return extract_concepts_with_relationships(text)

if __name__ == "__main__":
    # Test the enhanced PDF parser
    import sys
    
    if len(sys.argv) > 1:
        pdf_path = sys.argv[1]
        output_dir = sys.argv[2] if len(sys.argv) > 2 else None
        
        result = process_pdf_complete(pdf_path, output_dir)
        
        if result['success']:
            print("Processing successful!")
            print(result['summary'])
            if output_dir:
                print(f"\nFiles exported to: {output_dir}")
                for file_type, file_path in result['exported_files'].items():
                    print(f"- {file_type}: {file_path}")
        else:
            print(f"Processing failed: {result['error']}")
    else:
        print("Usage: python pdf_parser.py <pdf_path> [output_dir]")
