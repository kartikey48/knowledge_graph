#!/usr/bin/env python3
"""
Test script for knowledge graph generation using NetworkX and PyVis
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from backend.graph_visualizer import KnowledgeGraphVisualizer
from backend.extractor import extract_concepts_with_relationships

def test_with_sample_data():
    """Test graph generation with sample relationships."""
    
    # Sample relationships
    sample_relationships = [
        {"source": "Machine Learning", "target": "Artificial Intelligence", "relation": "is_part_of"},
        {"source": "Deep Learning", "target": "Machine Learning", "relation": "is_subset_of"},
        {"source": "Neural Networks", "target": "Deep Learning", "relation": "implements"},
        {"source": "Computer Vision", "target": "Deep Learning", "relation": "uses"},
        {"source": "Natural Language Processing", "target": "Machine Learning", "relation": "applies"},
        {"source": "Reinforcement Learning", "target": "Machine Learning", "relation": "is_type_of"},
        {"source": "Convolutional Neural Networks", "target": "Computer Vision", "relation": "enables"},
        {"source": "Recurrent Neural Networks", "target": "Natural Language Processing", "relation": "powers"},
        {"source": "Transformers", "target": "Natural Language Processing", "relation": "revolutionizes"},
        {"source": "BERT", "target": "Transformers", "relation": "implements"}
    ]
    
    print("Testing Knowledge Graph Generation...")
    print(f"Sample relationships: {len(sample_relationships)}")
    
    # Create visualizer
    visualizer = KnowledgeGraphVisualizer()
    
    # Generate graph
    result = visualizer.create_graph_from_relationships(sample_relationships)
    
    # Print metrics
    metrics = result["metrics"]
    print(f"\nGraph Metrics:")
    print(f"- Nodes: {metrics['num_nodes']}")
    print(f"- Edges: {metrics['num_edges']}")
    print(f"- Density: {metrics['density']:.3f}")
    print(f"- Most Central Node: {metrics['most_central_node']}")
    print(f"- Average Clustering: {metrics['avg_clustering']:.3f}")
    
    # Save HTML file
    output_file = "test_knowledge_graph.html"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(result["html_content"])
    
    print(f"\nGraph saved to: {output_file}")
    print("Open this file in a web browser to view the interactive graph.")
    
    return result

def test_with_text_extraction():
    """Test with actual text extraction."""
    
    sample_text = """
    Artificial intelligence (AI) is a rapidly evolving field that encompasses machine learning, 
    deep learning, and neural networks. Machine learning algorithms enable computers to learn 
    from data without explicit programming. Deep learning, a subset of machine learning, uses 
    neural networks with multiple layers to process complex patterns. Computer vision applies 
    deep learning techniques to analyze and understand visual information. Natural language 
    processing utilizes machine learning to understand and generate human language. 
    Reinforcement learning enables agents to learn through interaction with environments.
    Convolutional neural networks are particularly effective for image recognition tasks.
    Recurrent neural networks excel at processing sequential data like text and speech.
    Transformer architectures have revolutionized natural language processing tasks.
    """
    
    print("\nTesting with text extraction...")
    print(f"Sample text length: {len(sample_text)} characters")
    
    # Extract relationships
    relationships = extract_concepts_with_relationships(sample_text)
    print(f"Extracted relationships: {len(relationships)}")
    
    if relationships:
        # Create visualization
        visualizer = KnowledgeGraphVisualizer()
        result = visualizer.create_graph_from_relationships(relationships)
        
        # Save HTML file
        output_file = "extracted_knowledge_graph.html"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(result["html_content"])
        
        print(f"Extracted graph saved to: {output_file}")
        
        # Print some extracted relationships
        print("\nSample extracted relationships:")
        for i, rel in enumerate(relationships[:5]):
            print(f"  {i+1}. {rel['source']} --[{rel['relation']}]--> {rel['target']}")
    
    else:
        print("No relationships extracted. Check your Ollama setup.")

def main():
    """Main test function."""
    print("Knowledge Graph Generator Test")
    print("=" * 50)
    
    # Test 1: Sample data
    test_with_sample_data()
    
    # Test 2: Text extraction (requires Ollama)
    try:
        test_with_text_extraction()
    except Exception as e:
        print(f"\nText extraction test failed: {e}")
        print("Make sure Ollama is installed and running with a compatible model.")
    
    print("\n" + "=" * 50)
    print("Test completed!")

if __name__ == "__main__":
    main()