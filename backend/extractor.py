# backend/extractor.py
import subprocess
import json
import re
from typing import List, Dict, Any, Optional
import logging
import time
import threading
import os

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration constants
MAX_TEXT_LENGTH = 1500  # Reduced for more reliable processing
OLLAMA_TIMEOUT = 60  # Increased timeout
MAX_RELATIONSHIPS = 10  # Fewer relationships for better quality
CHUNK_SIZE = 1000

def check_ollama_service() -> bool:
    """Check if Ollama service is running and accessible."""
    try:
        result = subprocess.run(
            ['ollama', 'list'], 
            capture_output=True, 
            text=True, 
            timeout=10
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError, Exception) as e:
        logger.error(f"Ollama service check failed: {e}")
        return False

def get_available_models() -> List[str]:
    """Get list of available Ollama models."""
    try:
        result = subprocess.run(
            ['ollama', 'list'], 
            capture_output=True, 
            text=True, 
            timeout=10
        )
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')[1:]  # Skip header
            models = []
            for line in lines:
                if line.strip():
                    model_name = line.split()[0]  # First column is model name
                    models.append(model_name)
            return models
        return []
    except Exception as e:
        logger.error(f"Failed to get available models: {e}")
        return []

def extract_concepts_with_relationships(text: str) -> List[Dict[str, str]]:
    """
    Extract concepts and relationships from text using Ollama with improved error handling.
    """
    logger.info("Starting concept extraction...")
    
    # Check if Ollama is available
    if not check_ollama_service():
        logger.error("Ollama service is not available, using fallback extraction")
        return extract_with_rules(text)
    
    # Get available models
    available_models = get_available_models()
    logger.info(f"Available Ollama models: {available_models}")
    
    if not available_models:
        logger.warning("No Ollama models available, using fallback extraction")
        return extract_with_rules(text)
    
    # Try Ollama first
    ollama_result = extract_with_ollama(text, available_models)
    if ollama_result:
        logger.info(f"Ollama extraction successful: {len(ollama_result)} relationships")
        return ollama_result
    
    # Fallback to rule-based extraction
    logger.warning("Ollama extraction failed, using rule-based fallback")
    fallback_result = extract_with_rules(text)
    logger.info(f"Rule-based extraction: {len(fallback_result)} relationships")
    
    return fallback_result

def extract_with_ollama(text: str, available_models: List[str]) -> List[Dict[str, str]]:
    """
    Extract using Ollama with improved model selection and error handling.
    """
    # Preprocess text
    processed_text = preprocess_text(text)
    
    # Prioritize models (prefer smaller, faster models)
    model_priority = [
        'mistral:7b-instruct', 'mistral:7b', 'mistral',
        'llama2:7b-chat', 'llama2:7b', 'llama2',
        'phi', 'tinyllama', 'orca-mini'
    ]
    
    # Filter available models by priority
    models_to_try = []
    for model in model_priority:
        if model in available_models:
            models_to_try.append(model)
    
    # Add any other available models
    for model in available_models:
        if model not in models_to_try:
            models_to_try.append(model)
    
    if not models_to_try:
        logger.error("No suitable models found")
        return []
    
    logger.info(f"Trying models in order: {models_to_try[:3]}")  # Limit to 3 models
    
    # Use a much simpler, more reliable prompt
    prompt = f"""Extract key relationships from this text. Return exactly 5 relationships in JSON format.

Text: {processed_text[:MAX_TEXT_LENGTH]}

Format: [{{"source": "ConceptA", "relation": "uses", "target": "ConceptB"}}, ...]

Rules:
- Focus on technical concepts only
- Use simple relations: uses, enables, requires, improves, creates
- Keep concepts short (2-4 words max)
- Return valid JSON only

JSON:"""

    for model_name in models_to_try[:3]:  # Try max 3 models
        try:
            logger.info(f"Trying model: {model_name}")
            result = run_ollama_with_model(prompt, model_name)
            if result:
                relationships = parse_simple_format(result)
                if relationships:
                    logger.info(f"Successfully extracted {len(relationships)} relationships with {model_name}")
                    return relationships
            
        except Exception as e:
            logger.warning(f"Model {model_name} failed: {e}")
            continue
    
    logger.error("All Ollama models failed")
    return []

def run_ollama_with_model(prompt: str, model_name: str) -> Optional[str]:
    """
    Run Ollama with a specific model and improved timeout handling.
    """
    try:
        logger.info(f"Running Ollama with model: {model_name}")
        
        # Use Popen for better control
        process = subprocess.Popen(
            ['ollama', 'run', model_name],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )
        
        # Use threading for timeout control
        result = run_with_timeout(process, prompt, OLLAMA_TIMEOUT)
        
        if result is None:
            logger.warning(f"Ollama model {model_name} timed out")
            return None
        
        stdout, stderr = result
        
        if stderr.strip():
            logger.warning(f"Ollama stderr for {model_name}: {stderr.strip()}")
        
        if process.returncode == 0 and stdout.strip():
            return stdout.strip()
        else:
            logger.warning(f"Model {model_name} failed with return code: {process.returncode}")
            return None
            
    except Exception as e:
        logger.error(f"Error running model {model_name}: {e}")
        return None

def run_with_timeout(process, prompt, timeout):
    """
    Run subprocess with timeout using threading.
    """
    result = [None]
    exception = [None]
    
    def target():
        try:
            result[0] = process.communicate(input=prompt)
        except Exception as e:
            exception[0] = e
    
    thread = threading.Thread(target=target)
    thread.daemon = True
    thread.start()
    thread.join(timeout)
    
    if thread.is_alive():
        logger.warning("Process timeout, terminating...")
        process.terminate()
        thread.join(2)  # Wait 2 seconds for graceful termination
        if thread.is_alive():
            logger.warning("Force killing process...")
            process.kill()
            thread.join(1)
        return None
    
    if exception[0]:
        raise exception[0]
    
    return result[0]

def parse_simple_format(output: str) -> List[Dict[str, str]]:
    """
    Parse the output with multiple fallback strategies.
    """
    relationships = []
    
    # Strategy 1: Look for JSON array
    json_array_match = re.search(r'\[\s*\{.*?\}\s*\]', output, re.DOTALL)
    if json_array_match:
        try:
            parsed = json.loads(json_array_match.group())
            if isinstance(parsed, list):
                relationships.extend(parsed)
        except json.JSONDecodeError:
            pass
    
    # Strategy 2: Look for individual JSON objects
    json_objects = re.findall(r'\{[^{}]*"source"[^{}]*"target"[^{}]*\}', output)
    for obj_str in json_objects:
        try:
            obj = json.loads(obj_str)
            if all(key in obj for key in ['source', 'target']):
                relation = obj.get('relation', obj.get('relationship', 'relates_to'))
                relationships.append({
                    'source': str(obj['source']).strip(),
                    'target': str(obj['target']).strip(),
                    'relation': str(relation).strip()
                })
        except:
            continue
    
    # Strategy 3: Look for pipe-separated format
    lines = output.split('\n')
    for line in lines:
        if '|' in line:
            parts = line.split('|')
            if len(parts) >= 3:
                source = parts[0].strip()
                relation = parts[1].strip()
                target = parts[2].strip()
                
                if source and relation and target:
                    relationships.append({
                        'source': source,
                        'target': target,
                        'relation': relation
                    })
    
    return filter_and_deduplicate(relationships)

def extract_with_rules(text: str) -> List[Dict[str, str]]:
    """
    Enhanced rule-based extraction as fallback when Ollama fails.
    """
    logger.info("Using enhanced rule-based extraction...")
    
    # Clean text
    text = preprocess_text(text)
    
    # Extract potential concepts using NLP patterns
    concepts = extract_concepts_with_patterns(text)
    
    if len(concepts) < 2:
        logger.warning("Insufficient concepts found for relationship generation")
        return []
    
    # Generate relationships based on co-occurrence and patterns
    relationships = generate_relationships_from_concepts(concepts, text)
    
    return relationships

def extract_concepts_with_patterns(text: str) -> List[str]:
    """
    Extract concepts using regex patterns and NLP rules.
    """
    concepts = set()
    
    # Enhanced technical term patterns
    patterns = [
        r'\b[A-Z][a-z]+ [A-Z][a-z]+(?:\s+[A-Z][a-z]+)?\b',  # Title Case phrases
        r'\b(?:machine learning|deep learning|neural network|artificial intelligence|data mining|computer vision|natural language processing|knowledge graph|semantic analysis)\b',
        r'\b\w+(?:ing|tion|ment|ness|ity|ism|ics|ogy)\b',  # Words ending in common suffixes
        r'\b(?:algorithm|model|system|method|approach|technique|framework|architecture|protocol|standard|process|procedure)\w*\b',
        r'\b(?:analysis|evaluation|optimization|classification|prediction|detection|recognition|extraction|generation)\b',
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            cleaned = match.strip().title()
            if 3 <= len(cleaned) <= 30 and not cleaned.lower() in ['the', 'and', 'for', 'with']:
                concepts.add(cleaned)
    
    # Filter out very common words
    filtered_concepts = []
    common_words = {
        'The', 'This', 'That', 'With', 'From', 'They', 'Were', 'Been', 
        'Have', 'Will', 'Would', 'Could', 'Should', 'Data', 'Result', 
        'Method', 'Study', 'Research', 'Paper', 'Article', 'Work'
    }
    
    for concept in concepts:
        if concept not in common_words:
            filtered_concepts.append(concept)
    
    return list(filtered_concepts)[:15]  # Limit to top 15

def generate_relationships_from_concepts(concepts: List[str], text: str) -> List[Dict[str, str]]:
    """
    Generate relationships between concepts based on text analysis.
    """
    relationships = []
    text_lower = text.lower()
    
    # Enhanced relationship indicators
    relationship_patterns = {
        'uses': [' uses ', ' utilizing ', ' employs ', ' applies ', ' implements '],
        'enables': [' enables ', ' allows ', ' facilitates ', ' supports '],
        'improves': [' improves ', ' enhances ', ' optimizes ', ' increases '],
        'requires': [' requires ', ' needs ', ' depends on ', ' relies on '],
        'generates': [' generates ', ' produces ', ' creates ', ' outputs '],
        'analyzes': [' analyzes ', ' examines ', ' studies ', ' evaluates '],
        'processes': [' processes ', ' handles ', ' manages ', ' transforms ']
    }
    
    # Check concept pairs for relationships
    for i, concept1 in enumerate(concepts):
        for j, concept2 in enumerate(concepts):
            if i != j and concept1.lower() != concept2.lower():
                
                # Check if both concepts appear in text
                if concept1.lower() in text_lower and concept2.lower() in text_lower:
                    
                    # Look for relationship indicators between concepts
                    for relation, indicators in relationship_patterns.items():
                        for indicator in indicators:
                            # Check proximity and relationship indicators
                            pattern1 = f"{concept1.lower()}.*?{indicator}.*?{concept2.lower()}"
                            pattern2 = f"{concept2.lower()}.*?{indicator}.*?{concept1.lower()}"
                            
                            if (re.search(pattern1, text_lower, re.DOTALL) or 
                                re.search(pattern2, text_lower, re.DOTALL)):
                                relationships.append({
                                    'source': concept1,
                                    'target': concept2,
                                    'relation': relation
                                })
                                break
                        
                        if len(relationships) >= MAX_RELATIONSHIPS:
                            break
                
                if len(relationships) >= MAX_RELATIONSHIPS:
                    break
            
            if len(relationships) >= MAX_RELATIONSHIPS:
                break
    
    # If no relationships found, create some based on co-occurrence
    if not relationships and len(concepts) >= 2:
        logger.info("No pattern-based relationships found, creating co-occurrence relationships")
        for i in range(0, min(len(concepts)-1, 5)):
            relationships.append({
                'source': concepts[i],
                'target': concepts[i+1],
                'relation': 'relates_to'
            })
    
    return filter_and_deduplicate(relationships)

def preprocess_text(text: str) -> str:
    """
    Clean and preprocess text for better extraction.
    """
    # Remove excessive whitespace
    text = re.sub(r'\s+', ' ', text.strip())
    
    # Remove citations and references
    text = re.sub(r'\[\d+\]', '', text)
    text = re.sub(r'\([^)]*\d{4}[^)]*\)', '', text)
    
    # Remove figure/table references
    text = re.sub(r'\b(Figure|Table|Fig\.|Tab\.)\s+\d+[^\w]*', '', text)
    
    # Focus on meaningful sentences
    sentences = [s.strip() for s in text.split('.') if len(s.strip()) > 30]
    
    # Return first few sentences that contain technical terms
    technical_sentences = []
    technical_terms = ['algorithm', 'method', 'approach', 'system', 'model', 'technique', 'analysis', 'framework']
    
    for sentence in sentences:
        if any(term in sentence.lower() for term in technical_terms):
            technical_sentences.append(sentence)
        if len(technical_sentences) >= 5:
            break
    
    return '. '.join(technical_sentences) if technical_sentences else '. '.join(sentences[:3])

def filter_and_deduplicate(relationships: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """
    Filter and deduplicate relationships.
    """
    if not relationships:
        return []
    
    # Remove duplicates
    seen = set()
    unique_relationships = []
    
    for rel in relationships:
        # Create a normalized key for deduplication
        key = tuple(sorted([rel['source'].lower(), rel['target'].lower()]))
        if key not in seen:
            seen.add(key)
            unique_relationships.append(rel)
    
    # Limit to max relationships
    return unique_relationships[:MAX_RELATIONSHIPS]

def test_extraction():
    """
    Test the extraction with sample text.
    """
    sample_text = """
    Machine learning algorithms are widely used in artificial intelligence applications. 
    Deep learning techniques enable advanced pattern recognition in computer vision systems.
    Neural networks implement complex mathematical models for data analysis.
    Natural language processing requires sophisticated algorithms for text understanding.
    """
    
    print("Testing extraction...")
    start_time = time.time()
    
    relationships = extract_concepts_with_relationships(sample_text)
    
    end_time = time.time()
    print(f"Extraction completed in {end_time - start_time:.2f} seconds")
    print(f"Found {len(relationships)} relationships:")
    
    for rel in relationships:
        print(f"  {rel['source']} --[{rel['relation']}]--> {rel['target']}")
    
    return relationships

if __name__ == "__main__":
    test_extraction()
