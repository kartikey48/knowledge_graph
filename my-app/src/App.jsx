    import React, { useState, useCallback } from 'react';
    import FileUpload from './components/FileUpload';
    import GraphVisualization from './components/GraphVisualization';
    import NodeInteractionModal from './components/NodeInteractionModal';
    import Notification from './components/Notification';
    import './App.css';

    function App() {
      const [graphData, setGraphData] = useState(null);
      const [isLoading, setIsLoading] = useState(false);
      const [error, setError] = useState(null);
  
      // Modal state
      const [modalOpen, setModalOpen] = useState(false);
      const [selectedNode, setSelectedNode] = useState(null);
      const [searchResults, setSearchResults] = useState(null);
      const [isSearching, setIsSearching] = useState(false);
      const [isGeneratingGraph, setIsGeneratingGraph] = useState(false);
  
      // Notification state
      const [notification, setNotification] = useState(null);

      const showNotification = useCallback((message, type = 'info', duration = 5000) => {
        setNotification({ message, type, duration });
      }, []);

      const hideNotification = useCallback(() => {
        setNotification(null);
      }, []);

      const handleFileUpload = useCallback(async (file, options = {}) => {
        setIsLoading(true);
        setError(null);
        showNotification('Processing your document...', 'info', 0);

        try {
          const formData = new FormData();
          formData.append('file', file);
      
          Object.keys(options).forEach(key => {
            formData.append(key, options[key]);
          });

          const response = await fetch('http://localhost:8000/upload', {
            method: 'POST',
            body: formData,
          });

          if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Upload failed');
          }

          const data = await response.json();
          setGraphData(data);
          hideNotification();
          showNotification('Knowledge graph generated successfully!', 'success');
        } catch (err) {
          setError(err.message);
          hideNotification();
          showNotification(`Upload failed: ${err.message}`, 'error');
          console.error('Upload error:', err);
        } finally {
          setIsLoading(false);
        }
      }, [showNotification, hideNotification]);
      // Handle node click from graph
      const handleNodeClick = useCallback((nodeData) => {
        setSelectedNode(nodeData.label || nodeData.id);
        setSearchResults(null);
        setModalOpen(true);
        showNotification(`Exploring node: ${nodeData.label || nodeData.id}`, 'info', 3000);
      }, [showNotification]);

      // Handle paper search
      const handleSearchPapers = useCallback(async (node, domain) => {
        setIsSearching(true);
        setError(null);
        showNotification(`Searching for papers about "${node}" in ${domain}...`, 'info', 0);

        try {
          const response = await fetch('http://localhost:8000/search_papers_by_node', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({
              node: node,
              domain: domain
            }),
          });

          if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Search failed');
          }

          const data = await response.json();
          setSearchResults(data.papers);
          hideNotification();
          showNotification(`Found ${data.papers.length} related papers`, 'success');
        } catch (err) {
          setError(err.message);
          hideNotification();
          showNotification(`Search failed: ${err.message}`, 'error');
          console.error('Search error:', err);
          setSearchResults([]);
        } finally {
          setIsSearching(false);
        }
      }, [showNotification, hideNotification]);

      // Handle paper graph generation
      const handleGeneratePaperGraph = useCallback(async (paperId, paperUrl = null) => {
        setIsGeneratingGraph(true);
        setError(null);
        showNotification('Generating knowledge graph from paper...', 'info', 0);

        try {
          const response = await fetch('http://localhost:8000/generate_paper_graph', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({
              paper_id: paperId,
              paper_url: paperUrl
            }),
          });

          if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Graph generation failed');
          }

          const data = await response.json();
          
          // Update the main graph with the new paper graph
          setGraphData({
            metadata: data.metadata,
            graph: data.graph
          });
          
          // Close the modal
          setModalOpen(false);
          setSearchResults(null);
          
          hideNotification();
          showNotification(
            `Successfully generated knowledge graph for: ${data.paper_info.title.substring(0, 50)}...`, 
            'success'
          );
          
        } catch (err) {
          setError(err.message);
          hideNotification();
          showNotification(`Failed to generate graph: ${err.message}`, 'error');
          console.error('Graph generation error:', err);
        } finally {
          setIsGeneratingGraph(false);
        }
      }, [showNotification, hideNotification]);

      const handleCloseModal = useCallback(() => {
        setModalOpen(false);
        setSelectedNode(null);
        setSearchResults(null);
        setError(null);
      }, []);

      return (
        <div className="App">
          <header className="App-header">
            <h1>Knowledge Graph Generator</h1>
            <p>Upload a PDF to extract and visualize knowledge relationships</p>
          </header>

          <main className="App-main">
            {error && (
              <div className="error-message">
                <h3>Error</h3>
                <p>{error}</p>
                <button onClick={() => setError(null)}>Dismiss</button>
              </div>
            )}

            <FileUpload 
              onFileUpload={handleFileUpload} 
              isLoading={isLoading}
            />

            {isLoading && (
              <div className="loading-container">
                <div className="loading-spinner"></div>
                <p>Processing your document...</p>
                <small>This may take a few minutes depending on document size</small>
              </div>
            )}

            {graphData && !isLoading && (
              <div className="graph-container">
                <div className="graph-header">
                  <h2>Knowledge Graph</h2>
                  {graphData.metadata && (
                    <div className="graph-stats">
                      <span>Nodes: {graphData.metadata.num_nodes || 0}</span>
                      <span>Edges: {graphData.metadata.num_edges || 0}</span>
                      {graphData.metadata.paper_title && (
                        <span>Paper: {graphData.metadata.paper_title}</span>
                      )}
                    </div>
                  )}
                </div>
                
                <GraphVisualization 
                  data={graphData.graph} 
                  onNodeClick={handleNodeClick}
                />
                
                {graphData.metadata && (
                  <div className="metadata-panel">
                    <h3>Document Information</h3>
                    <div className="metadata-grid">
                      {graphData.metadata.filename && (
                        <div className="metadata-item">
                          <strong>File:</strong> {graphData.metadata.filename}
                        </div>
                      )}
                      {graphData.metadata.paper_title && (
                        <div className="metadata-item">
                          <strong>Title:</strong> {graphData.metadata.paper_title}
                        </div>
                      )}
                      {graphData.metadata.paper_authors && (
                        <div className="metadata-item">
                          <strong>Authors:</strong> {graphData.metadata.paper_authors.join(', ')}
                        </div>
                      )}
                      {graphData.metadata.paper_year && (
                        <div className="metadata-item">
                          <strong>Year:</strong> {graphData.metadata.paper_year}
                        </div>
                      )}
                      <div className="metadata-item">
                        <strong>Text Length:</strong> {graphData.metadata.text_length?.toLocaleString()} characters
                      </div>
                      <div className="metadata-item">
                        <strong>Relationships:</strong> {graphData.metadata.num_relationships}
                      </div>
                      {graphData.metadata.analysis && (
                        <>
                          <div className="metadata-item">
                            <strong>Graph Density:</strong> {graphData.metadata.analysis.density}
                          </div>
                          <div className="metadata-item">
                            <strong>Average Degree:</strong> {graphData.metadata.analysis.avg_degree}
                          </div>
                        </>
                      )}
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Instructions */}
            {!graphData && !isLoading && (
              <div className="instructions">
                <h2>How to use</h2>
                <ol>
                  <li>Upload a PDF document using the file selector above</li>
                  <li>Wait for the system to process and extract concepts</li>
                  <li>Explore the generated knowledge graph</li>
                  <li><strong>Click on any node</strong> to search for related research papers</li>
                  <li>Select a domain and search for papers related to that concept</li>
                  <li><strong>Generate knowledge graphs</strong> from related papers</li>
                  <li>Compare different papers and their concept relationships</li>
                </ol>
                
                <div className="feature-highlights">
                  <h3>Features</h3>
                  <ul>
                    <li>🔍 Interactive node exploration</li>
                    <li>📚 Research paper discovery</li>
                    <li>🌐 Multi-domain search</li>
                    <li>📊 Graph-to-graph comparison</li>
                    <li>🎯 Semantic relationship extraction</li>
                  </ul>
                </div>
              </div>
            )}
          </main>

          {/* Node Interaction Modal */}
          <NodeInteractionModal
            isOpen={modalOpen}
            onClose={handleCloseModal}
            selectedNode={selectedNode}
            onSearchPapers={handleSearchPapers}
            onGeneratePaperGraph={handleGeneratePaperGraph}
            searchResults={searchResults}
            isSearching={isSearching}
            isGeneratingGraph={isGeneratingGraph}
          />

          <Notification
            message={notification?.message}
            type={notification?.type}
            onClose={hideNotification}
            duration={notification?.duration}
          />
        </div>
      );
    }

    export default App;