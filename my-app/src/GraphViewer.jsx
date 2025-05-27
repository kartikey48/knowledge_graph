import React, { useEffect, useRef, useState } from 'react';
import cytoscape from 'cytoscape';
import cola from 'cytoscape-cola';
import dagre from 'cytoscape-dagre';
import { ZoomIn, ZoomOut, Maximize2, RotateCcw, Download, Settings } from 'lucide-react';

// Register extensions
cytoscape.use(cola);
cytoscape.use(dagre);

const GraphViewer = ({ elements, onNodeClick, selectedNode }) => {
  const cyRef = useRef(null);
  const containerRef = useRef(null);
  const [cy, setCy] = useState(null);
  const [layout, setLayout] = useState('cola');
  const [showControls, setShowControls] = useState(true);
  const [graphStats, setGraphStats] = useState({ nodes: 0, edges: 0 });

  // Enhanced layout configurations
  const layoutConfigs = {
    cola: {
      name: 'cola',
      animate: true,
      refresh: 1,
      maxSimulationTime: 4000,
      ungrabifyWhileSimulating: false,
      fit: true,
      padding: 30,
      nodeSpacing: function(node) { return 10; },
      edgeLength: function(edge) { return 80; },
      edgeSymDiffLength: 20,
      edgeJaccardLength: 20,
      unconstrIter: 1,
      userConstIter: 0,
      allConstIter: 1,
      infinite: false
    },
    dagre: {
      name: 'dagre',
      fit: true,
      padding: 30,
      spacingFactor: 1.25,
      nodeDimensionsIncludeLabels: true,
      animate: true,
      animationDuration: 1000,
      rankDir: 'TB',
      ranker: 'network-simplex'
    },
    circle: {
      name: 'circle',
      fit: true,
      padding: 30,
      boundingBox: undefined,
      avoidOverlap: true,
      nodeDimensionsIncludeLabels: false,
      spacingFactor: undefined,
      radius: undefined,
      startAngle: 3 / 2 * Math.PI,
      sweep: undefined,
      clockwise: true,
      sort: undefined,
      animate: true,
      animationDuration: 1000
    },
    grid: {
      name: 'grid',
      fit: true,
      padding: 30,
      boundingBox: undefined,
      avoidOverlap: true,
      avoidOverlapPadding: 10,
      nodeDimensionsIncludeLabels: false,
      spacingFactor: undefined,
      condense: false,
      rows: undefined,
      cols: undefined,
      position: function(node) {},
      sort: undefined,
      animate: true,
      animationDuration: 1000
    },
    cose: {
      name: 'cose',
      fit: true,
      padding: 30,
      boundingBox: undefined,
      nodeDimensionsIncludeLabels: false,
      randomize: false,
      componentSpacing: 40,
      nodeRepulsion: function(node) { return 2048; },
      nodeOverlap: 4,
      idealEdgeLength: function(edge) { return 32; },
      edgeElasticity: function(edge) { return 32; },
      nestingFactor: 1.2,
      gravity: 1,
      numIter: 1000,
      initialTemp: 1000,
      coolingFactor: 0.99,
      minTemp: 1.0,
      animate: true,
      animationDuration: 1000
    }
  };

  // Enhanced style configuration
  const styleConfig = [
    {
      selector: 'node',
      style: {
        'background-color': function(ele) {
          if (ele.data('type') === 'concept') return '#3B82F6';
          if (ele.data('type') === 'entity') return '#10B981';
          if (ele.data('type') === 'method') return '#8B5CF6';
          return '#6B7280';
        },
        'label': 'data(label)',
        'width': function(ele) {
          const degree = ele.degree();
          return Math.max(20, Math.min(60, 20 + degree * 3));
        },
        'height': function(ele) {
          const degree = ele.degree();
          return Math.max(20, Math.min(60, 20 + degree * 3));
        },
        'text-valign': 'center',
        'text-halign': 'center',
        'color': '#FFFFFF',
        'font-size': function(ele) {
          const degree = ele.degree();
          return Math.max(10, Math.min(16, 10 + degree));
        },
        'font-weight': 'bold',
        'text-outline-width': 2,
        'text-outline-color': function(ele) {
          if (ele.data('type') === 'concept') return '#1E40AF';
          if (ele.data('type') === 'entity') return '#047857';
          if (ele.data('type') === 'method') return '#5B21B6';
          return '#374151';
        },
        'text-wrap': 'wrap',
        'text-max-width': '80px',
        'overlay-padding': '6px',
        'z-index': 10,
        'border-width': 2,
        'border-color': '#FFFFFF',
        'transition-property': 'background-color, border-color, width, height',
        'transition-duration': '0.3s'
      }
    },
    {
      selector: 'node:selected',
      style: {
        'border-width': 4,
        'border-color': '#F59E0B',
        'background-color': '#F59E0B',
        'z-index': 20
      }
    },
    {
      selector: 'node:hover',
      style: {
        'border-width': 3,
        'border-color': '#EF4444',
        'cursor': 'pointer'
      }
    },
    {
      selector: 'edge',
      style: {
        'width': function(ele) {
          const weight = ele.data('weight') || 1;
          return Math.max(1, Math.min(6, weight * 2));
        },
        'line-color': function(ele) {
          const relation = ele.data('label') || '';
          if (relation.includes('enables') || relation.includes('improves')) return '#10B981';
          if (relation.includes('requires') || relation.includes('depends')) return '#EF4444';
          if (relation.includes('uses') || relation.includes('applies')) return '#3B82F6';
          return '#6B7280';
        },
        'target-arrow-color': function(ele) {
          const relation = ele.data('label') || '';
          if (relation.includes('enables') || relation.includes('improves')) return '#10B981';
          if (relation.includes('requires') || relation.includes('depends')) return '#EF4444';
          if (relation.includes('uses') || relation.includes('applies')) return '#3B82F6';
          return '#6B7280';
        },
        'target-arrow-shape': 'triangle',
        'curve-style': 'bezier',
        'label': 'data(label)',
        'font-size': '12px', // Increased font size
        'font-weight': 'bold', // Added bold font weight
        'color': '#FFFFFF', // White text color
        'text-rotation': 'autorotate',
        'text-margin-y': -10,
        'text-background-color': '#000000', // Solid black background
        'text-background-opacity': 0.8,
        'text-background-padding': '4px', // Increased padding
        'text-border-width': 0, // Removed border to simplify
        'text-outline-width': 2, // Added text outline for better visibility
        'text-outline-color': '#000000', // Black outline
        'opacity': 0.8,
        'z-index': 5,
        'transition-property': 'line-color, width, opacity',
        'transition-duration': '0.3s'
      }
    },
    {
      selector: 'edge:hover',
      style: {
        'opacity': 1,
        'width': function(ele) {
          const weight = ele.data('weight') || 1;
          return Math.max(2, Math.min(8, weight * 3));
        },
        'z-index': 15,
        'color': '#FFFFFF', // White text on hover
        'font-size': '14px', // Larger font on hover
        'text-background-color': '#000000',
        'text-background-opacity': 0.9,
        'text-outline-width': 2,
        'text-outline-color': '#000000'
      }
    },
    {
      selector: 'edge:selected',
      style: {
        'line-color': '#F59E0B',
        'target-arrow-color': '#F59E0B',
        'opacity': 1,
        'z-index': 20,
        'color': '#FFFFFF', // White text when selected
        'font-size': '14px',
        'text-background-color': '#F59E0B',
        'text-background-opacity': 0.8,
        'text-outline-width': 2,
        'text-outline-color': '#000000'
      }
    }
    ,
    {
      selector: '.highlighted',
      style: {
        'background-color': '#F59E0B',
        'line-color': '#F59E0B',
        'target-arrow-color': '#F59E0B',
        'color': '#FFFFFF',
        'transition-property': 'background-color, line-color, target-arrow-color',
        'transition-duration': '0.3s'
      }
    },
    {
      selector: '.faded',
      style: {
        'opacity': 0.3,
        'transition-property': 'opacity',
        'transition-duration': '0.3s'
      }
    }
  ];
  useEffect(() => {
    if (!containerRef.current || !elements || elements.length === 0) return;

    // Clean up existing instance
    if (cyRef.current) {
      cyRef.current.destroy();
    }

    // Calculate graph statistics
    const nodes = elements.filter(el => el.data.id && !el.data.source);
    const edges = elements.filter(el => el.data.source && el.data.target);
    setGraphStats({ nodes: nodes.length, edges: edges.length });

    // Initialize Cytoscape
    const cyInstance = cytoscape({
      container: containerRef.current,
      elements: elements,
      style: styleConfig,
      layout: layoutConfigs[layout],
      minZoom: 0.1,
      maxZoom: 3,
      wheelSensitivity: 0.2,
      motionBlur: true,
      selectionType: 'single',
      boxSelectionEnabled: false,
      autoungrabify: false,
      autounselectify: false
    });

    // Enhanced event handlers
    cyInstance.on('tap', 'node', (event) => {
      const node = event.target;
      const nodeId = node.data('id');
      
      // Highlight connected elements
      const connectedEdges = node.connectedEdges();
      const connectedNodes = connectedEdges.connectedNodes();
      
      // Reset all elements
      cyInstance.elements().removeClass('highlighted faded');
      
      // Highlight connected elements
      node.addClass('highlighted');
      connectedEdges.addClass('highlighted');
      connectedNodes.addClass('highlighted');
      
      // Fade non-connected elements
      cyInstance.elements().not(node).not(connectedEdges).not(connectedNodes).addClass('faded');
      
      if (onNodeClick) {
        onNodeClick(event);
      }
    });

    cyInstance.on('tap', 'edge', (event) => {
      const edge = event.target;
      const sourceNode = edge.source();
      const targetNode = edge.target();
      
      // Reset all elements
      cyInstance.elements().removeClass('highlighted faded');
      
      // Highlight edge and connected nodes
      edge.addClass('highlighted');
      sourceNode.addClass('highlighted');
      targetNode.addClass('highlighted');
      
      // Fade other elements
      cyInstance.elements().not(edge).not(sourceNode).not(targetNode).addClass('faded');
    });

    cyInstance.on('tap', (event) => {
      // If clicking on background, reset highlighting
      if (event.target === cyInstance) {
        cyInstance.elements().removeClass('highlighted faded');
      }
    });

    // Mouse hover effects
    cyInstance.on('mouseover', 'node', (event) => {
      const node = event.target;
      const tooltip = `${node.data('label')} (${node.degree()} connections)`;
      node.qtip({
        content: tooltip,
        position: {
          my: 'bottom center',
          at: 'top center'
        },
        style: {
          classes: 'qtip-bootstrap',
          tip: {
            width: 16,
            height: 8
          }
        },
        show: {
          event: false,
          ready: true
        },
        hide: {
          event: 'mouseout unfocus'
        }
      });
    });

    cyInstance.on('mouseover', 'edge', (event) => {
      const edge = event.target;
      const tooltip = `${edge.source().data('label')} → ${edge.data('label')} → ${edge.target().data('label')}`;
      edge.qtip({
        content: tooltip,
        position: {
          my: 'bottom center',
          at: 'top center'
        },
        style: {
          classes: 'qtip-bootstrap',
          tip: {
            width: 16,
            height: 8
          }
        },
        show: {
          event: false,
          ready: true
        },
        hide: {
          event: 'mouseout unfocus'
        }
      });
    });

    cyRef.current = cyInstance;
    setCy(cyInstance);

    return () => {
      if (cyRef.current) {
        cyRef.current.destroy();
      }
    };
  }, [elements, layout, onNodeClick]);

  // Update selected node highlighting
  useEffect(() => {
    if (!cy || !selectedNode) return;

    cy.elements().removeClass('highlighted faded');
    
    const node = cy.getElementById(selectedNode);
    if (node.length > 0) {
      const connectedEdges = node.connectedEdges();
      const connectedNodes = connectedEdges.connectedNodes();
      
      node.addClass('highlighted');
      connectedEdges.addClass('highlighted');
      connectedNodes.addClass('highlighted');
      
      cy.elements().not(node).not(connectedEdges).not(connectedNodes).addClass('faded');
    }
  }, [selectedNode, cy]);

  const handleZoomIn = () => {
    if (cy) {
      cy.zoom(cy.zoom() * 1.2);
      cy.center();
    }
  };

  const handleZoomOut = () => {
    if (cy) {
      cy.zoom(cy.zoom() * 0.8);
      cy.center();
    }
  };

  const handleFit = () => {
    if (cy) {
      cy.fit();
    }
  };

  const handleReset = () => {
    if (cy) {
      cy.elements().removeClass('highlighted faded');
      cy.fit();
      cy.zoom(1);
    }
  };

  const handleLayoutChange = (newLayout) => {
    setLayout(newLayout);
    if (cy) {
      const layoutConfig = layoutConfigs[newLayout];
      cy.layout(layoutConfig).run();
    }
  };

  const handleExportImage = () => {
    if (cy) {
      const png64 = cy.png({ scale: 2, full: true });
      const link = document.createElement('a');
      link.download = 'knowledge-graph.png';
      link.href = png64;
      link.click();
    }
  };

  if (!elements || elements.length === 0) {
    return (
      <div className="flex items-center justify-center h-full bg-gray-50">
        <div className="text-center">
          <div className="w-16 h-16 mx-auto mb-4 bg-gray-200 rounded-full flex items-center justify-center">
            <svg className="w-8 h-8 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
          </div>
          <h3 className="text-lg font-medium text-gray-900 mb-2">No Graph Data</h3>
          <p className="text-gray-500">Upload a PDF file to generate and visualize the knowledge graph</p>
        </div>
      </div>
    );
  }

  return (
    <div className="relative w-full h-full">
      <style>
        {`
          .cy-edge-text {
            color: white !important
            fill: white !important
          }
        `}
      </style>
      {/* Graph Container */}
      <div ref={containerRef} className="w-full h-full bg-white" />
      
      {/* Controls Panel */}      {showControls && (
        <div className="absolute top-4 left-4 bg-white rounded-lg shadow-lg border border-gray-200 p-3 space-y-2 z-10">
          {/* Graph Stats */}
          <div className="text-xs text-gray-600 border-b border-gray-200 pb-2 mb-2">
            <div>{graphStats.nodes} nodes</div>
            <div>{graphStats.edges} edges</div>
          </div>
          
          {/* Zoom Controls */}
          <div className="flex space-x-1">
            <button
              onClick={handleZoomIn}
              className="p-2 text-gray-600 hover:text-gray-800 hover:bg-gray-100 rounded transition-colors"
              title="Zoom In"
            >
              <ZoomIn className="w-4 h-4" />
            </button>
            <button
              onClick={handleZoomOut}
              className="p-2 text-gray-600 hover:text-gray-800 hover:bg-gray-100 rounded transition-colors"
              title="Zoom Out"
            >
              <ZoomOut className="w-4 h-4" />
            </button>
            <button
              onClick={handleFit}
              className="p-2 text-gray-600 hover:text-gray-800 hover:bg-gray-100 rounded transition-colors"
              title="Fit to Screen"
            >
              <Maximize2 className="w-4 h-4" />
            </button>
            <button
              onClick={handleReset}
              className="p-2 text-gray-600 hover:text-gray-800 hover:bg-gray-100 rounded transition-colors"
              title="Reset View"
            >
              <RotateCcw className="w-4 h-4" />
            </button>
          </div>
          
          {/* Layout Selection */}
          <div className="border-t border-gray-200 pt-2">
            <label className="block text-xs font-medium text-gray-700 mb-1">Layout</label>
            <select
              value={layout}
              onChange={(e) => handleLayoutChange(e.target.value)}
              className="w-full text-xs border border-gray-300 rounded px-2 py-1 focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="cola">Cola (Force)</option>
              <option value="dagre">Dagre (Hierarchical)</option>
              <option value="circle">Circle</option>
              <option value="grid">Grid</option>
              <option value="cose">Cose (Physics)</option>
            </select>
          </div>
          
          {/* Export Button */}
          <button
            onClick={handleExportImage}
            className="w-full flex items-center justify-center gap-1 px-3 py-2 text-xs bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors"
            title="Export as PNG"
          >
            <Download className="w-3 h-3" />
            Export PNG
          </button>
        </div>
      )}
      
      {/* Toggle Controls Button */}
      <button
        onClick={() => setShowControls(!showControls)}
        className="absolute top-4 right-4 p-2 bg-white rounded-lg shadow-lg border border-gray-200 text-gray-600 hover:text-gray-800 hover:bg-gray-100 transition-colors z-10"
        title={showControls ? "Hide Controls" : "Show Controls"}
      >
        <Settings className="w-4 h-4" />
      </button>
      
      {/* Legend */}
      <div className="absolute bottom-4 left-4 bg-white rounded-lg shadow-lg border border-gray-200 p-3 z-10">
        <h4 className="text-xs font-medium text-gray-700 mb-2">Legend</h4>
        <div className="space-y-1 text-xs">
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 bg-blue-500 rounded-full"></div>
            <span className="text-gray-600">Concept</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 bg-green-500 rounded-full"></div>
            <span className="text-gray-600">Entity</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 bg-purple-500 rounded-full"></div>
            <span className="text-gray-600">Method</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-1 bg-green-500"></div>
            <span className="text-gray-600">Enables/Improves</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-1 bg-red-500"></div>
            <span className="text-gray-600">Requires/Depends</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-1 bg-blue-500"></div>
            <span className="text-gray-600">Uses/Applies</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default GraphViewer;