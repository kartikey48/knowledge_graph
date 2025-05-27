import React, { useEffect, useRef, useState } from 'react';
import cytoscape from 'cytoscape';
import dagre from 'cytoscape-dagre';
import cose from 'cytoscape-cose-bilkent';

// Register layout extensions
cytoscape.use(dagre);
cytoscape.use(cose);

const GraphVisualization = ({ graphData, onNodeClick }) => {
  const cyRef = useRef(null);
  const containerRef = useRef(null);
  const [layout, setLayout] = useState('dagre');

  useEffect(() => {
    if (!graphData || !containerRef.current) return;

    // Destroy existing instance
    if (cyRef.current) {
      cyRef.current.destroy();
    }

    // Create new Cytoscape instance with optimized settings
    cyRef.current = cytoscape({
      container: containerRef.current,
      
      elements: graphData,
      
      style: [
        // Node styles
        {
          selector: 'node',
          style: {
            'background-color': '#4A90E2',
            'border-width': 2,
            'border-color': '#2E5C8A',
            'label': 'data(label)',
            'text-valign': 'center',
            'text-halign': 'center',
            'color': '#FFFFFF',
            'font-size': '12px',
            'font-weight': 'bold',
            'font-family': 'Arial, sans-serif',
            'text-wrap': 'wrap',
            'text-max-width': '80px',
            'width': 'label',
            'height': 'label',
            'padding': '10px',
            'shape': 'round-rectangle',
            'min-width': '60px',
            'min-height': '30px',
            'text-outline-width': 1,
            'text-outline-color': '#2E5C8A',
            'overlay-opacity': 0,
            'transition-property': 'background-color, border-color, width, height',
            'transition-duration': '0.3s'
          }
        },
        
        // Node hover effects
        {
          selector: 'node:hover',
          style: {
            'background-color': '#5BA0F2',
            'border-color': '#1E4C7A',
            'cursor': 'pointer',
            'z-index': 999
          }
        },
        
        // Selected node style
        {
          selector: 'node:selected',
          style: {
            'background-color': '#FF6B6B',
            'border-color': '#E55555',
            'border-width': 3
          }
        },
        
        // Edge styles
        {
          selector: 'edge',
          style: {
            'width': 2,
            'line-color': '#666666',
            'target-arrow-color': '#666666',
            'target-arrow-shape': 'triangle',
            'curve-style': 'bezier',
            'arrow-scale': 1.2,
            'label': 'data(label)',
            'font-size': '10px',
            'font-weight': 'normal',
            'color': '#444444',
            'text-rotation': 'autorotate',
            'text-margin-y': -10,
            'text-background-color': '#FFFFFF',
            'text-background-opacity': 0.8,
            'text-background-padding': '2px',
            'text-border-width': 1,
            'text-border-color': '#CCCCCC',
            'overlay-opacity': 0,
            'transition-property': 'line-color, target-arrow-color, width',
            'transition-duration': '0.3s'
          }
        },
        
        // Edge hover effects
        {
          selector: 'edge:hover',
          style: {
            'line-color': '#4A90E2',
            'target-arrow-color': '#4A90E2',
            'width': 3,
            'z-index': 999
          }
        },
        
        // Selected edge style
        {
          selector: 'edge:selected',
          style: {
            'line-color': '#FF6B6B',
            'target-arrow-color': '#FF6B6B',
            'width': 3
          }
        }
      ],
      
      layout: getLayoutConfig(layout, graphData.length),
      
      // Interaction settings
      minZoom: 0.1,
      maxZoom: 3,
      wheelSensitivity: 0.2,
      motionBlur: true,
      selectionType: 'single',
      boxSelectionEnabled: false,
      autoungrabify: false,
      autounselectify: false
    });

    // Add event listeners
    cyRef.current.on('tap', 'node', (event) => {
      const node = event.target;
      if (onNodeClick) {
        onNodeClick(node.data());
      }
    });

    // Auto-fit and center
    cyRef.current.fit();
    cyRef.current.center();

    // Cleanup function
    return () => {
      if (cyRef.current) {
        cyRef.current.destroy();
      }
    };
  }, [graphData, layout, onNodeClick]);

  const getLayoutConfig = (layoutName, nodeCount) => {
    const baseConfig = {
      animate: true,
      animationDuration: 1000,
      animationEasing: 'ease-out',
      fit: true,
      padding: 50
    };

    switch (layoutName) {
      case 'dagre':
        return {
          ...baseConfig,
          name: 'dagre',
          rankDir: 'TB', // Top to bottom
          align: 'UL', // Upper left alignment
          ranker: 'longest-path',
          nodeSep: 80, // Horizontal separation between nodes
          edgeSep: 20, // Separation between edges
          rankSep: 100, // Vertical separation between ranks
          marginX: 20,
          marginY: 20
        };
      
      case 'cose':
        return {
          ...baseConfig,
          name: 'cose-bilkent',
          quality: 'default',
          nodeDimensionsIncludeLabels: true,
          refresh: 30,
          randomize: false,
          nodeRepulsion: nodeCount > 20 ? 8000 : 4500,
          idealEdgeLength: nodeCount > 20 ? 100 : 80,
          edgeElasticity: 0.45,
          nestingFactor: 0.1,
          gravity: 0.25,
          numIter: 2500,
          tile: true,
          tilingPaddingVertical: 20,
          tilingPaddingHorizontal: 20
        };
      
      case 'circle':
        return {
          ...baseConfig,
          name: 'circle',
          radius: Math.max(200, nodeCount * 15),
          spacing: 1.5
        };
      
      case 'grid':
        return {
          ...baseConfig,
          name: 'grid',
          rows: Math.ceil(Math.sqrt(nodeCount)),
          cols: Math.ceil(Math.sqrt(nodeCount)),
          spacingFactor: 2
        };
      
      default:
        return {
          ...baseConfig,
          name: 'cose',
          idealEdgeLength: 100,
          nodeOverlap: 20,
          refresh: 20,
          componentSpacing: 100,
          nodeRepulsion: 400000,
          edgeElasticity: 100,
          nestingFactor: 5,
          gravity: 80,
          numIter: 1000,
          initialTemp: 200,
          coolingFactor: 0.95,
          minTemp: 1.0
        };
    }
  };

  const handleLayoutChange = (newLayout) => {
    setLayout(newLayout);
    if (cyRef.current) {
      const layoutConfig = getLayoutConfig(newLayout, graphData.length);
      const layoutInstance = cyRef.current.layout(layoutConfig);
      layoutInstance.run();
    }
  };

  const handleFitGraph = () => {
    if (cyRef.current) {
      cyRef.current.fit();
      cyRef.current.center();
    }
  };

  const handleResetZoom = () => {
    if (cyRef.current) {
      cyRef.current.zoom(1);
      cyRef.current.center();
    }
  };

  const handleExportImage = () => {
    if (cyRef.current) {
      const png64 = cyRef.current.png({ scale: 2, full: true });
      const link = document.createElement('a');
      link.download = 'knowledge-graph.png';
      link.href = png64;
      link.click();
    }
  };

  return (
    <div className="graph-container">
      {/* Control Panel */}
      <div className="graph-controls">
        <div className="control-group">
          <label>Layout:</label>
          <select 
            value={layout} 
            onChange={(e) => handleLayoutChange(e.target.value)}
            className="layout-select"
          >
            <option value="dagre">Hierarchical (Dagre)</option>
            <option value="cose">Force-directed (COSE)</option>
            <option value="circle">Circular</option>
            <option value="grid">Grid</option>
          </select>
        </div>
        
        <div className="control-group">
          <button onClick={handleFitGraph} className="control-btn">
            Fit to Screen
          </button>
          <button onClick={handleResetZoom} className="control-btn">
            Reset Zoom
          </button>
          <button onClick={handleExportImage} className="control-btn">
            Export PNG
          </button>
        </div>
      </div>

      {/* Graph Container */}
      <div 
        ref={containerRef} 
        className="cytoscape-container"
        style={{
          width: '100%',
          height: '600px',
          border: '1px solid #ddd',
          borderRadius: '8px',
          backgroundColor: '#fafafa'
        }}
      />

      {/* Graph Info */}
      {graphData && (
        <div className="graph-info">
          <span>Nodes: {graphData.filter(el => !el.data.source).length}</span>
          <span>Edges: {graphData.filter(el => el.data.source).length}</span>
        </div>
      )}
    </div>
  );
};

export default GraphVisualization;