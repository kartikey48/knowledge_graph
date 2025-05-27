import React, { useEffect, useRef, useState } from 'react';
import cytoscape from 'cytoscape';
import './GraphVisualization.css';

const GraphVisualization = ({ data, onNodeClick }) => {
  const cyRef = useRef(null);
  const containerRef = useRef(null);
  const [cy, setCy] = useState(null);
  const [layout, setLayout] = useState('cose');

  useEffect(() => {
    if (!data || !containerRef.current) return;

    // Initialize Cytoscape
    const cyInstance = cytoscape({
      container: containerRef.current,
      elements: data,
      style: [
        {
          selector: 'node',
          style: {
            'background-color': '#667eea',
            'label': 'data(label)',
            'color': '#ffffff',
            'text-valign': 'center',
            'text-halign': 'center',
            'font-size': '12px',
            'font-weight': 'bold',
            'width': 'mapData(degree, 1, 10, 30, 80)',
            'height': 'mapData(degree, 1, 10, 30, 80)',
            'text-wrap': 'wrap',
            'text-max-width': '80px',
            'border-width': 2,
            'border-color': '#4c51bf',
            'text-outline-width': 2,
            'text-outline-color': '#667eea',
            'transition-property': 'background-color, border-color, width, height',
            'transition-duration': '0.3s'
          }
        },
        {
          selector: 'node:hover',
          style: {
            'background-color': '#5a67d8',
            'border-color': '#2d3748',
            'cursor': 'pointer'
          }
        },
        {
          selector: 'node:selected',
          style: {
            'background-color': '#e53e3e',
            'border-color': '#c53030',
            'border-width': 3
          }
        },
        {
          selector: 'edge',
          style: {
            'width': 'mapData(weight, 1, 10, 2, 8)',
            'line-color': '#a0aec0',
            'target-arrow-color': '#a0aec0',
            'target-arrow-shape': 'triangle',
            'curve-style': 'bezier',
            'label': 'data(label)',
            'font-size': '10px',
            'color': '#4a5568',
            'text-rotation': 'autorotate',
            'text-margin-y': -10,
            'opacity': 0.8,
            'transition-property': 'line-color, target-arrow-color, width',
            'transition-duration': '0.3s'
          }
        },
        {
          selector: 'edge:hover',
          style: {
            'line-color': '#667eea',
            'target-arrow-color': '#667eea',
            'opacity': 1
          }
        },
        {
          selector: 'edge:selected',
          style: {
            'line-color': '#e53e3e',
            'target-arrow-color': '#e53e3e',
            'width': 4
          }
        }
      ],
      layout: {
        name: layout,
        animate: true,
        animationDuration: 1000,
        fit: true,
        padding: 50,
        randomize: false,
        componentSpacing: 100,
        nodeRepulsion: 400000,
        nodeOverlap: 10,
        idealEdgeLength: 100,
        edgeElasticity: 100,
        nestingFactor: 5,
        gravity: 80,
        numIter: 1000,
        initialTemp: 200,
        coolingFactor: 0.95,
        minTemp: 1.0
      },
      wheelSensitivity: 0.2,
      minZoom: 0.1,
      maxZoom: 3
    });

    // Add event listeners
    cyInstance.on('tap', 'node', (event) => {
      const node = event.target;
      if (onNodeClick) {
        onNodeClick({
          id: node.id(),
          label: node.data('label'),
          data: node.data()
        });
      }
    });

    // Add double-click to fit
    cyInstance.on('dblclick', () => {
      cyInstance.fit();
    });

    setCy(cyInstance);
    cyRef.current = cyInstance;

    return () => {
      if (cyInstance) {
        cyInstance.destroy();
      }
    };
  }, [data, layout, onNodeClick]);

  const handleLayoutChange = (newLayout) => {
    setLayout(newLayout);
    if (cy) {
      cy.layout({
        name: newLayout,
        animate: true,
        animationDuration: 1000,
        fit: true,
        padding: 50
      }).run();
    }
  };

  const handleFit = () => {
    if (cy) {
      cy.fit();
    }
  };

  const handleCenter = () => {
    if (cy) {
      cy.center();
    }
  };

  const handleReset = () => {
    if (cy) {
      cy.zoom(1);
      cy.center();
    }
  };

  if (!data || data.length === 0) {
    return (
      <div className="graph-placeholder">
        <div className="placeholder-content">
          <div className="placeholder-icon">🔍</div>
          <h3>No Graph Data</h3>
          <p>Upload a PDF document to generate a knowledge graph</p>
        </div>
      </div>
    );
  }

  return (
    <div className="graph-visualization">
      <div className="graph-controls">
        <select 
          value={layout} 
          onChange={(e) => handleLayoutChange(e.target.value)}
          className="layout-selector"
        >
          <option value="cose">Force-directed</option>
          <option value="circle">Circle</option>
          <option value="grid">Grid</option>
          <option value="breadthfirst">Hierarchical</option>
          <option value="concentric">Concentric</option>
        </select>
        <button onClick={handleFit} title="Fit to view">
          🔍
        </button>
        <button onClick={handleCenter} title="Center graph">
          🎯
        </button>
        <button onClick={handleReset} title="Reset zoom">
          🔄
        </button>
        <button onClick={() => cyRef.current?.zoom(cyRef.current.zoom() * 1.2)}>
          Zoom In
        </button>
        <button onClick={() => cyRef.current?.zoom(cyRef.current.zoom() * 0.8)}>
          Zoom Out
        </button>
      </div>
      
      <div className="graph-instructions">
        <p>💡 Click on any node to explore related research papers</p>
        <ul>
          <li>Drag to pan • Scroll to zoom • Double-click to fit</li>
          <li>Hover over edges to see relationship types</li>
          <li>Use layout controls to change visualization style</li>
        </ul>
      </div>
      
      <div 
        ref={containerRef} 
        className="cytoscape-container"
        style={{ width: '100%', height: '600px' }}
      />
    </div>
  );
};

export default GraphVisualization;