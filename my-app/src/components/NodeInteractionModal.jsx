import React, { useState, useEffect } from 'react';
import './NodeInteractionModal.css';

const NodeInteractionModal = ({
  isOpen,
  onClose,
  selectedNode,
  onSearchPapers,
  onGeneratePaperGraph,
  searchResults,
  isSearching,
  isGeneratingGraph
}) => {
  const [domain, setDomain] = useState('computer science');
  const [searchQuery, setSearchQuery] = useState('');

  const domains = [
    'computer science',
    'artificial intelligence',
    'machine learning',
    'data science',
    'software engineering',
    'information systems',
    'human-computer interaction',
    'cybersecurity',
    'bioinformatics',
    'computational biology',
    'physics',
    'mathematics',
    'chemistry',
    'biology',
    'medicine',
    'psychology',
    'economics',
    'business',
    'engineering',
    'materials science'
  ];

  useEffect(() => {
    if (selectedNode) {
      setSearchQuery(selectedNode);
    }
  }, [selectedNode]);

  const handleSearch = () => {
    if (searchQuery.trim() && domain) {
      onSearchPapers(searchQuery.trim(), domain);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter') {
      handleSearch();
    }
  };

  const handleGenerateGraph = (paper) => {
    onGeneratePaperGraph(paper.paperId, paper.url);
  };

  if (!isOpen) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Explore: {selectedNode}</h2>
          <button className="modal-close" onClick={onClose}>
            ×
          </button>
        </div>

        <div className="modal-body">
          <div className="search-section">
            <h3>Search Related Papers</h3>
            <div className="search-form">
              <div className="form-group">
                <label htmlFor="search-query">Search Term:</label>
                <input
                  id="search-query"
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  onKeyPress={handleKeyPress}
                  placeholder="Enter concept to search..."
                  disabled={isSearching}
                />
              </div>
              
              <div className="form-group">
                <label htmlFor="domain-select">Domain:</label>
                <select
                  id="domain-select"
                  value={domain}
                  onChange={(e) => setDomain(e.target.value)}
                  disabled={isSearching}
                >
                  {domains.map((d) => (
                    <option key={d} value={d}>
                      {d.charAt(0).toUpperCase() + d.slice(1)}
                    </option>
                  ))}
                </select>
              </div>
              
              <button
                onClick={handleSearch}
                disabled={isSearching || !searchQuery.trim()}
                className="search-button"
              >
                {isSearching ? (
                  <>
                    <span className="button-spinner"></span>
                    Searching...
                  </>
                ) : (
                  'Search Papers'
                )}
              </button>
            </div>
          </div>

          {searchResults && (
            <div className="results-section">
              <h3>Search Results ({searchResults.length} papers found)</h3>
              {searchResults.length === 0 ? (
                <div className="no-results">
                  <p>No papers found for this search. Try:</p>
                  <ul>
                    <li>Using different keywords</li>
                    <li>Selecting a different domain</li>
                    <li>Using broader search terms</li>
                  </ul>
                </div>
              ) : (
                <div className="papers-list">
                  {searchResults.map((paper, index) => (
                    <div key={paper.paperId || index} className="paper-item">
                      <div className="paper-header">
                        <h4 className="paper-title">
                          {paper.url ? (
                            <a href={paper.url} target="_blank" rel="noopener noreferrer">
                              {paper.title}
                            </a>
                          ) : (
                            paper.title
                          )}
                        </h4>
                        <div className="paper-meta">
                          {paper.year && <span className="paper-year">{paper.year}</span>}
                          {paper.citationCount !== undefined && (
                            <span className="citation-count">
                              📄 {paper.citationCount} citations
                            </span>
                          )}
                        </div>
                      </div>
                      
                      {paper.authors && paper.authors.length > 0 && (
                        <div className="paper-authors">
                          <strong>Authors:</strong> {paper.authors.slice(0, 3).join(', ')}
                          {paper.authors.length > 3 && ` +${paper.authors.length - 3} more`}
                        </div>
                      )}
                      
                      {paper.abstract && (
                        <div className="paper-abstract">
                          <strong>Abstract:</strong> 
                          <p>{paper.abstract.length > 300 
                            ? `${paper.abstract.substring(0, 300)}...` 
                            : paper.abstract}
                          </p>
                        </div>
                      )}
                      
                      {paper.venue && (
                        <div className="paper-venue">
                          <strong>Published in:</strong> {paper.venue}
                        </div>
                      )}
                      
                      <div className="paper-actions">
                        {paper.url && (
                          <a 
                            href={paper.url} 
                            target="_blank" 
                            rel="noopener noreferrer"
                            className="action-button view-paper"
                          >
                            View Paper
                          </a>
                        )}
                        {paper.paperId && (
                          <button
                            onClick={() => handleGenerateGraph(paper)}
                            disabled={isGeneratingGraph}
                            className="action-button generate-graph"
                          >
                            {isGeneratingGraph ? (
                              <>
                                <span className="button-spinner"></span>
                                Generating...
                              </>
                            ) : (
                              'Generate Graph'
                            )}
                          </button>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {isSearching && (
            <div className="loading-state">
              <div className="spinner"></div>
              <p>Searching for papers...</p>
            </div>
          )}

          {isGeneratingGraph && (
            <div className="loading-state">
              <div className="spinner"></div>
              <p>Generating knowledge graph...</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default NodeInteractionModal;