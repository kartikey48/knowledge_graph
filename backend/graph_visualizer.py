"""
Enhanced graph visualization with community detection and improved layout.
"""

import networkx as nx
import numpy as np
from pyvis.network import Network
from typing import List, Dict, Any, Tuple, Optional
import logging
import colorsys
import math
from collections import defaultdict, Counter
import community as community_louvain  # python-louvain
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

logger = logging.getLogger(__name__)

class EnhancedGraphVisualizer:
    """Enhanced graph visualizer with community detection and contextual proximity."""
    
    def __init__(self):
        self.color_palette = self._generate_color_palette(20)
        self.node_colors = {}
        self.community_colors = {}
        
    def _generate_color_palette(self, n_colors: int) -> List[str]:
        """Generate a diverse color palette."""
        colors = []
        for i in range(n_colors):
            hue = i / n_colors
            saturation = 0.7 + (i % 3) * 0.1  # Vary saturation
            lightness = 0.5 + (i % 2) * 0.2   # Vary lightness
            rgb = colorsys.hls_to_rgb(hue, lightness, saturation)
            hex_color = '#{:02x}{:02x}{:02x}'.format(
                int(rgb[0] * 255), int(rgb[1] * 255), int(rgb[2] * 255)
            )
            colors.append(hex_color)
        return colors
    
    def calculate_contextual_proximity(self, relationships: List[Dict[str, str]], 
                                     original_text: str) -> Dict[Tuple[str, str], float]:
        """
        Calculate contextual proximity scores between concepts based on text co-occurrence.
        """
        logger.info("Calculating contextual proximity...")
        
        # Extract all unique concepts
        concepts = set()
        for rel in relationships:
            concepts.add(rel['source'])
            concepts.add(rel['target'])
        
        concepts = list(concepts)
        proximity_scores = {}
        
        # Split text into sentences
        sentences = [s.strip() for s in original_text.split('.') if len(s.strip()) > 20]
        
        # Calculate co-occurrence in sentences
        concept_sentences = defaultdict(list)
        
        for i, sentence in enumerate(sentences):
            sentence_lower = sentence.lower()
            for concept in concepts:
                if concept.lower() in sentence_lower:
                    concept_sentences[concept].append(i)
        
        # Calculate proximity scores
        for i, concept1 in enumerate(concepts):
            for j, concept2 in enumerate(concepts):
                if i < j:  # Avoid duplicates
                    sentences1 = set(concept_sentences[concept1])
                    sentences2 = set(concept_sentences[concept2])
                    
                    if sentences1 and sentences2:
                        # Calculate proximity based on sentence distance
                        min_distance = float('inf')
                        for s1 in sentences1:
                            for s2 in sentences2:
                                distance = abs(s1 - s2)
                                min_distance = min(min_distance, distance)
                        
                        # Convert distance to proximity score (closer = higher score)
                        if min_distance == 0:  # Same sentence
                            proximity = 1.0
                        else:
                            proximity = 1.0 / (1.0 + min_distance * 0.1)
                        
                        # Boost score for co-occurrence frequency
                        common_sentences = len(sentences1.intersection(sentences2))
                        if common_sentences > 0:
                            proximity += common_sentences * 0.2
                        
                        proximity_scores[(concept1, concept2)] = min(proximity, 1.0)
        
        logger.info(f"Calculated proximity for {len(proximity_scores)} concept pairs")
        return proximity_scores
    
    def detect_communities(self, graph: nx.Graph) -> Dict[str, int]:
        """
        Detect communities in the graph using Louvain algorithm.
        """
        logger.info("Detecting communities...")
        
        try:
            # Use Louvain community detection
            communities = community_louvain.best_partition(graph, resolution=1.2)
            
            # Log community information
            community_sizes = Counter(communities.values())
            logger.info(f"Found {len(community_sizes)} communities")
            for comm_id, size in community_sizes.most_common():
                logger.info(f"  Community {comm_id}: {size} nodes")
            
            return communities
            
        except Exception as e:
            logger.warning(f"Community detection failed: {e}")
            # Fallback: assign all nodes to one community
            return {node: 0 for node in graph.nodes()}
    
    def filter_weak_connections(self, relationships: List[Dict[str, str]], 
                               proximity_scores: Dict[Tuple[str, str], float],
                               threshold: float = 0.1) -> List[Dict[str, str]]:
        """
        Filter out weak connections based on contextual proximity.
        """
        filtered_relationships = []
        
        for rel in relationships:
            source, target = rel['source'], rel['target']
            
            # Check proximity score
            proximity = proximity_scores.get((source, target), 
                                           proximity_scores.get((target, source), 0.0))
            
            # Keep relationship if proximity is above threshold or if it's a strong semantic relation
            strong_relations = {'enables', 'requires', 'implements', 'uses', 'creates', 'improves'}
            
            if proximity >= threshold or rel['relation'] in strong_relations:
                rel['proximity_score'] = proximity
                filtered_relationships.append(rel)
            else:
                logger.debug(f"Filtered weak connection: {source} -> {target} (proximity: {proximity:.3f})")
        
        logger.info(f"Filtered {len(relationships) - len(filtered_relationships)} weak connections")
        return filtered_relationships
    
    def calculate_node_importance(self, graph: nx.Graph, 
                                 proximity_scores: Dict[Tuple[str, str], float]) -> Dict[str, float]:
        """
        Calculate node importance based on centrality measures and contextual proximity.
        """
        importance_scores = {}
        
        # Calculate various centrality measures
        try:
            betweenness = nx.betweenness_centrality(graph)
            closeness = nx.closeness_centrality(graph)
            degree = nx.degree_centrality(graph)
            eigenvector = nx.eigenvector_centrality(graph, max_iter=1000)
        except:
            # Fallback to simpler measures
            betweenness = {node: 0 for node in graph.nodes()}
            closeness = {node: 0 for node in graph.nodes()}
            degree = nx.degree_centrality(graph)
            eigenvector = {node: 0 for node in graph.nodes()}
        
        # Combine centrality measures with proximity-based importance
        for node in graph.nodes():
            # Base importance from centrality measures
            centrality_score = (
                betweenness.get(node, 0) * 0.3 +
                closeness.get(node, 0) * 0.2 +
                degree.get(node, 0) * 0.3 +
                eigenvector.get(node, 0) * 0.2
            )
            
            # Boost importance based on high-proximity connections
            proximity_boost = 0
            for neighbor in graph.neighbors(node):
                proximity = proximity_scores.get((node, neighbor), 
                                               proximity_scores.get((neighbor, node), 0))
                proximity_boost += proximity
            
            # Normalize proximity boost
            if graph.degree(node) > 0:
                proximity_boost /= graph.degree(node)
            
            # Final importance score
            importance_scores[node] = centrality_score + proximity_boost * 0.3
        
        return importance_scores
    
    def create_hierarchical_layout(self, graph: nx.Graph, 
                                  communities: Dict[str, int],
                                  importance_scores: Dict[str, float]) -> Dict[str, Tuple[float, float]]:
        """
        Create a hierarchical layout based on importance and communities.
        """
        positions = {}
        
        # Group nodes by community
        community_nodes = defaultdict(list)
        for node, comm in communities.items():
            community_nodes[comm].append(node)
        
        # Sort communities by average importance
        community_importance = {}
        for comm, nodes in community_nodes.items():
            avg_importance = np.mean([importance_scores.get(node, 0) for node in nodes])
            community_importance[comm] = avg_importance
        
        sorted_communities = sorted(community_importance.items(), key=lambda x: x[1], reverse=True)
        
        # Layout communities in a circular pattern
        n_communities = len(sorted_communities)
        community_positions = {}
        
        for i, (comm, _) in enumerate(sorted_communities):
            angle = 2 * np.pi * i / n_communities
            radius = 300  # Base radius for community centers
            x = radius * np.cos(angle)
            y = radius * np.sin(angle)
            community_positions[comm] = (x, y)
        
        # Position nodes within each community
        for comm, nodes in community_nodes.items():
            center_x, center_y = community_positions[comm]
            
            # Sort nodes by importance within community
            nodes_with_importance = [(node, importance_scores.get(node, 0)) for node in nodes]
            nodes_with_importance.sort(key=lambda x: x[1], reverse=True)
            
            # Create sub-layout for community
            n_nodes = len(nodes)
            if n_nodes == 1:
                positions[nodes[0]] = (center_x, center_y)
            else:
                # Arrange in concentric circles based on importance
                for i, (node, importance) in enumerate(nodes_with_importance):
                    if i == 0:  # Most important node at center
                        positions[node] = (center_x, center_y)
                    else:
                        # Place others in circles around center
                        circle_radius = 50 + (i // 6) * 30  # Increase radius for outer circles
                        angle = 2 * np.pi * (i % 6) / 6  # 6 nodes per circle
                        x = center_x + circle_radius * np.cos(angle)
                        y = center_y + circle_radius * np.sin(angle)
                        positions[node] = (x, y)
        
        return positions
    
    def create_enhanced_visualization(self, relationships: List[Dict[str, str]], 
                                    original_text: str,
                                    layout: str = "force",
                                    width: str = "100%", 
                                    height: str = "600px") -> Dict[str, Any]:
        """
        Create enhanced visualization with community detection and contextual proximity.
        """
        logger.info("Creating enhanced graph visualization...")
        
        # Calculate contextual proximity
        proximity_scores = self.calculate_contextual_proximity(relationships, original_text)
        
        # Filter weak connections
        filtered_relationships = self.filter_weak_connections(relationships, proximity_scores)
        
        if not filtered_relationships:
            logger.warning("No relationships after filtering")
            return self._create_empty_graph()
        
        # Create NetworkX graph
        G = nx.Graph()
        
        # Add nodes and edges
        for rel in filtered_relationships:
            G.add_edge(rel['source'], rel['target'], 
                      relation=rel['relation'],
                      proximity=rel.get('proximity_score', 0))
        
        # Detect communities
        communities = self.detect_communities(G)
        
        # Calculate node importance
        importance_scores = self.calculate_node_importance(G, proximity_scores)
        
        # Create Pyvis network
        net = Network(width=width, height=height, bgcolor="#fafafa", font_color="#333333")
        
        # Configure physics
        if layout == "force":
            net.set_options("""
            var options = {
              "physics": {
                "enabled": true,
                "stabilization": {"iterations": 100},
                "barnesHut": {
                  "gravitationalConstant": -8000,
                  "centralGravity": 0.3,
                  "springLength": 95,
                  "springConstant": 0.04,
                  "damping": 0.09,
                  "avoidOverlap": 1
                }
              },
              "interaction": {
                "hover": true,
                "tooltipDelay": 200
              },
              "nodes": {
                "font": {
                  "size": 14,
                  "color": "#000000",
                  "strokeWidth": 2,
                  "strokeColor": "#ffffff"
                },
                "borderWidth": 2,
                "shadow": true
              },
              "edges": {
                "font": {
                  "size": 12,
                  "color": "#000000",
                  "strokeWidth": 1,
                  "strokeColor": "#ffffff"
                },
                "shadow": true,
                "smooth": {
                  "type": "continuous"
                }
              }
            }
            """)
        
        # Assign colors to communities
        unique_communities = set(communities.values())
        for i, comm in enumerate(unique_communities):
            self.community_colors[comm] = self.color_palette[i % len(self.color_palette)]
        
        # Add nodes with enhanced styling
        for node in G.nodes():
            community = communities[node]
            importance = importance_scores.get(node, 0)
            
            # Node size based on importance
            size = 20 + importance * 40  # Size range: 20-60
            
            # Node color based on community
            color = self.community_colors[community]
            
            # Create tooltip with detailed information
            neighbors = list(G.neighbors(node))
            tooltip = f"""
            <b>{node}</b><br>
            Community: {community}<br>
            Importance: {importance:.3f}<br>
            Connections: {len(neighbors)}<br>
            Connected to: {', '.join(neighbors[:5])}{'...' if len(neighbors) > 5 else ''}
            """
            
            # Add node with enhanced styling
            net.add_node(
                node,
                label=self._wrap_text(node, 15),  # Wrap long text
                size=size,
                color={
                    'background': color,
                    'border': self._darken_color(color),
                    'highlight': {'background': self._lighten_color(color), 'border': color}
                },
                title=tooltip,
                font={'size': max(12, int(size/3)), 'color': '#000000', 'strokeWidth': 2, 'strokeColor': '#ffffff'},
                borderWidth=2,
                shadow=True
            )
        
        # Add edges with enhanced styling
        edge_colors = {
            'enables': '#4CAF50',
            'improves': '#2196F3',
            'requires': '#FF9800',
            'uses': '#009688',
            'implements': '#8BC34A',
            'creates': '#E91E63',
            'analyzes': '#9C27B0',
            'facilitates': '#607D8B',
            'emphasizes': '#E91E63',
            'encountered': '#FF5722',
            'highlights': '#3F51B5',
            'created for': '#795548',
            'relates_to': '#666666',
            'depends_on': '#795548',
            'contains': '#607D8B',
            'produces': '#FFC107'
        }
        
        for edge in G.edges(data=True):
            source, target, data = edge
            relation = data.get('relation', 'relates_to')
            proximity = data.get('proximity', 0)
            
            # Edge width based on proximity score
            width = 1 + proximity * 4  # Width range: 1-5
            
            # Edge color based on relation type
            edge_color = edge_colors.get(relation, '#666666')
            
            # Create edge tooltip
            tooltip = f"{source} → {target}<br>Relation: {relation}<br>Proximity: {proximity:.3f}"
            
            net.add_edge(
                source, 
                target,
                label=relation,
                width=width,
                color={'color': edge_color, 'highlight': self._lighten_color(edge_color)},
                title=tooltip,
                font={'size': 10, 'color': '#000000', 'strokeWidth': 1, 'strokeColor': '#ffffff'},
                shadow=True
            )
        
        # Apply custom layout if hierarchical
        if layout == "hierarchical":
            positions = self.create_hierarchical_layout(G, communities, importance_scores)
            for node, (x, y) in positions.items():
                net.get_node(node)['x'] = x
                net.get_node(node)['y'] = y
                net.get_node(node)['physics'] = False
        
        # Generate HTML
        html_content = net.generate_html()
        
        # Add custom CSS and JavaScript for better styling
        enhanced_html = self._enhance_html(html_content, communities, importance_scores)
        
        # Prepare metadata
        metadata = {
            'total_nodes': len(G.nodes()),
            'total_edges': len(G.edges()),
            'communities': len(unique_communities),
            'avg_clustering': nx.average_clustering(G),
            'density': nx.density(G),
            'community_info': {
                comm: {
                    'size': len([n for n, c in communities.items() if c == comm]),
                    'color': self.community_colors[comm],
                    'nodes': [n for n, c in communities.items() if c == comm]
                }
                for comm in unique_communities
            },
            'top_nodes': sorted(importance_scores.items(), key=lambda x: x[1], reverse=True)[:5]
        }
        
        logger.info(f"Enhanced visualization created: {metadata['total_nodes']} nodes, {metadata['total_edges']} edges, {metadata['communities']} communities")
        
        return {
            'html': enhanced_html,
            'metadata': metadata,
            'communities': communities,
            'importance_scores': importance_scores
        }
    
    def _wrap_text(self, text: str, max_length: int) -> str:
        """Wrap text to fit in nodes better."""
        if len(text) <= max_length:
            return text
        
        words = text.split()
        lines = []
        current_line = []
        current_length = 0
        
        for word in words:
            if current_length + len(word) + 1 <= max_length:
                current_line.append(word)
                current_length += len(word) + 1
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                current_line = [word]
                current_length = len(word)
        
        if current_line:
            lines.append(' '.join(current_line))
        
        return '\n'.join(lines)
    
    def _darken_color(self, hex_color: str, factor: float = 0.7) -> str:
        """Darken a hex color."""
        hex_color = hex_color.lstrip('#')
        rgb = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        darkened = tuple(int(c * factor) for c in rgb)
        return '#{:02x}{:02x}{:02x}'.format(*darkened)
    
    def _lighten_color(self, hex_color: str, factor: float = 1.3) -> str:
        """Lighten a hex color."""
        hex_color = hex_color.lstrip('#')
        rgb = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        lightened = tuple(min(255, int(c * factor)) for c in rgb)
        return '#{:02x}{:02x}{:02x}'.format(*lightened)
    
    def _enhance_html(self, html_content: str, communities: Dict[str, int], 
                     importance_scores: Dict[str, float]) -> str:
        """Add custom CSS and JavaScript to enhance the visualization."""
        
        # Custom CSS for better text visibility and styling
        custom_css = """
        <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        }
        
        #mynetworkid {
            border: 2px solid #ddd;
            border-radius: 10px;
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
            background: white;
        }
        
        .graph-controls {
            position: absolute;
            top: 10px;
            right: 10px;
            z-index: 1000;
            background: rgba(255,255,255,0.9);
            padding: 10px;
            border-radius: 5px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        
        .graph-controls button {
            margin: 2px;
            padding: 5px 10px;
            border: none;
            border-radius: 3px;
            background: #007bff;
            color: white;
            cursor: pointer;
            font-size: 12px;
        }
        
        .graph-controls button:hover {
            background: #0056b3;
        }
        
        .community-legend {
            position: absolute;
            top: 10px;
            left: 10px;
            z-index: 1000;
            background: rgba(255,255,255,0.9);
            padding: 10px;
            border-radius: 5px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            max-width: 200px;
        }
        
        .community-item {
            display: flex;
            align-items: center;
            margin: 3px 0;
            font-size: 12px;
        }
        
        .community-color {
            width: 12px;
            height: 12px;
            border-radius: 50%;
            margin-right: 8px;
            border: 1px solid #333;
        }
        
        .stats-panel {
            position: absolute;
            bottom: 10px;
            left: 10px;
            z-index: 1000;
            background: rgba(255,255,255,0.9);
            padding: 10px;
            border-radius: 5px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            font-size: 12px;
        }
        </style>
        """
        
        # Custom JavaScript for enhanced interactions
        custom_js = """
        <script>
        // Enhanced graph interactions
        function fitGraph() {
            network.fit();
        }
        
        function togglePhysics() {
            var options = network.getOptionsFromConfigurator();
            options.physics.enabled = !options.physics.enabled;
            network.setOptions(options);
        }
        
        function exportImage() {
            var canvas = document.querySelector('#mynetworkid canvas');
            var link = document.createElement('a');
            link.download = 'knowledge_graph.png';
            link.href = canvas.toDataURL();
            link.click();
        }
        
        function highlightCommunity(communityId) {
            // Implementation for highlighting specific communities
            console.log('Highlighting community:', communityId);
        }
        
        // Add event listeners after network is created
        network.on("selectNode", function (params) {
            if (params.nodes.length > 0) {
                var nodeId = params.nodes[0];
                console.log('Selected node:', nodeId);
                // Highlight connected nodes
                var connectedNodes = network.getConnectedNodes(nodeId);
                var updateArray = [];
                for (var i = 0; i < connectedNodes.length; i++) {
                    updateArray.push({id: connectedNodes[i], color: {border: '#ff0000'}});
                }
                nodes.update(updateArray);
            }
        });
        
        network.on("deselectNode", function (params) {
            // Reset node colors
            var allNodes = nodes.get();
            nodes.update(allNodes);
        });
        </script>
        """
        
        # Create community legend HTML
        community_legend = "<div class='community-legend'><h4>Communities</h4>"
        unique_communities = set(communities.values())
        for comm in sorted(unique_communities):
            color = self.community_colors.get(comm, '#666666')
            nodes_in_comm = [n for n, c in communities.items() if c == comm]
            community_legend += f"""
            <div class='community-item'>
                <div class='community-color' style='background-color: {color}'></div>
                <span>Community {comm} ({len(nodes_in_comm)} nodes)</span>
            </div>
            """
        community_legend += "</div>"
        
        # Create controls HTML
        controls_html = """
        <div class='graph-controls'>
            <button onclick='fitGraph()'>Fit Graph</button>
            <button onclick='togglePhysics()'>Toggle Physics</button>
            <button onclick='exportImage()'>Export PNG</button>
        </div>
        """
        
        # Create stats panel HTML
        stats_html = f"""
        <div class='stats-panel'>
            <h4>Graph Statistics</h4>
            <div>Nodes: {len(set(communities.keys()))}</div>
            <div>Communities: {len(unique_communities)}</div>
            <div>Top Node: {max(importance_scores.items(), key=lambda x: x[1])[0] if importance_scores else 'N/A'}</div>
        </div>
        """
        
        # Insert custom elements into HTML
        enhanced_html = html_content.replace(
            '</head>',
            f'{custom_css}</head>'
        ).replace(
            '</body>',
            f'{custom_js}{community_legend}{controls_html}{stats_html}</body>'
        )
        
        return enhanced_html
    
    def _create_legend(self) -> str:
        """Create legend for edge colors."""
        legend_items = []
        for relation, color in self.edge_colors.items():
            legend_items.append(f'''
                <div class="legend-item">
                    <div class="legend-color" style="background-color: {color};"></div>
                    <span>{relation.replace('_', ' ').title()}</span>
                </div>
            ''')
        
        return f'''
        <div class="legend">
            <div class="legend-title">Relationship Types</div>
            {''.join(legend_items)}
        </div>
        '''
    
    def _create_stats_panel(self) -> str:
        """Create statistics panel."""
        num_nodes = len(self.graph.nodes())
        num_edges = len(self.graph.edges())
        
        return f'''
        <div class="stats-panel">
            <div><strong>Graph Statistics</strong></div>
            <div>Nodes: {num_nodes}</div>
            <div>Edges: {num_edges}</div>
            <div>Density: {self._calculate_density():.3f}</div>
        </div>
        '''
    
    def _calculate_graph_metrics(self) -> Dict[str, Any]:
        """Calculate various graph metrics."""
        if len(self.graph.nodes()) == 0:
            return {
                "num_nodes": 0,
                "num_edges": 0,
                "density": 0,
                "most_central_node": None,
                "avg_clustering": 0
            }
        
        try:
            # Basic metrics
            num_nodes = len(self.graph.nodes())
            num_edges = len(self.graph.edges())
            density = self._calculate_density()
            
            # Centrality measures
            degree_centrality = nx.degree_centrality(self.graph)
            most_central_node = max(degree_centrality, key=degree_centrality.get) if degree_centrality else None
            
            # Clustering coefficient
            try:
                # Convert to undirected for clustering calculation
                undirected_graph = self.graph.to_undirected()
                avg_clustering = nx.average_clustering(undirected_graph)
            except:
                avg_clustering = 0
            
            return {
                "num_nodes": num_nodes,
                "num_edges": num_edges,
                "density": density,
                "most_central_node": most_central_node,
                "avg_clustering": avg_clustering,
                "degree_centrality": degree_centrality
            }
            
        except Exception as e:
            logger.error(f"Error calculating metrics: {e}")
            return {
                "num_nodes": len(self.graph.nodes()),
                "num_edges": len(self.graph.edges()),
                "density": 0,
                "most_central_node": None,
                "avg_clustering": 0
            }
    
    def _calculate_density(self) -> float:
        """Calculate graph density."""
        try:
            return nx.density(self.graph)
        except:
            return 0.0
    
    def _get_graph_data(self) -> Dict[str, Any]:
        """Get graph data in a structured format."""
        nodes = []
        edges = []
        
        for node, data in self.graph.nodes(data=True):
            nodes.append({
                "id": node,
                "label": data.get('label', node),
                "size": data.get('size', 25),
                "color": self.node_colors.get(node, '#45B7D1'),
                "importance": data.get('importance', 0)
            })
        
        for source, target, data in self.graph.edges(data=True):
            edges.append({
                "source": source,
                "target": target,
                "relation": data.get('relation', 'relates_to'),
                "color": self.edge_colors.get(data.get('relation', 'relates_to'), '#666666')
            })
        
        return {
            "nodes": nodes,
            "edges": edges
        }
    
    def _create_empty_graph(self) -> Dict[str, Any]:

        """Create an empty graph when no relationships are found."""
        net = Network(width="100%", height="400px", bgcolor="#fafafa")
        net.add_node("No Data", label="No relationships found", size=30, color="#cccccc")
        
        return {







            'html': net.generate_html(),
            'metadata': {
                'total_nodes': 0,
                'total_edges': 0,
                'communities': 0,
                'message': 'No valid relationships could be extracted from the document'
            },

            'communities': {},
            'importance_scores': {}
        }
    
    def _create_error_html(self, error_message: str) -> str:
        """Create error HTML."""
        return f"""
        <html>
        <head>
            <title>Graph Visualization Error</title>
            <style>
                body {{ font-family: Arial, sans-serif; padding: 20px; }}
                .error {{ color: red; background: #ffe6e6; padding: 15px; border-radius: 5px; }}
            </style>
        </head>
        <body>
            <h2>Graph Visualization Error</h2>
            <div class="error">
                <strong>Error:</strong> {error_message}
            </div>
            <p>Please try again or contact support if the problem persists.</p>
        </body>
        </html>
        """

# Layout-specific functions
def create_hierarchical_layout(relationships: List[Dict[str, str]]) -> str:
    """Create hierarchical layout visualization."""
    try:
        net = Network(height="600px", width="100%", bgcolor="#fafafa", directed=True)
        
        # Build graph to determine hierarchy
        graph = nx.DiGraph()
        for rel in relationships:
            graph.add_edge(rel['source'], rel['target'], relation=rel['relation'])
        
        # Calculate levels using topological sort
        try:
            levels = {}
            for i, node in enumerate(nx.topological_sort(graph)):
                levels[node] = i
        except nx.NetworkXError:
            # If graph has cycles, use degree-based leveling
            levels = {}
            in_degrees = dict(graph.in_degree())
            max_level = 0
            for node in graph.nodes():
                level = in_degrees.get(node, 0)
                levels[node] = level
                max_level = max(max_level, level)
        
        # Add nodes with hierarchical positioning
        for node in graph.nodes():
            level = levels.get(node, 0)
            net.add_node(
                node,
                label=node,
                level=level,
                color='#4CAF50' if level == 0 else '#2196F3',
                size=30,
                physics=False
            )
        
        # Add edges
        for source, target, data in graph.edges(data=True):
            net.add_edge(source, target, label=data.get('relation', ''))
        
        # Set hierarchical layout options
        net.set_options("""
        var options = {
          "layout": {
            "hierarchical": {
              "enabled": true,
              "direction": "UD",
              "sortMethod": "directed",
              "levelSeparation": 150,
              "nodeSpacing": 100
            }
          },
          "physics": {"enabled": false}
        }
        """)
        
        return net.generate_html()
        
    except Exception as e:
        logger.error(f"Error creating hierarchical layout: {e}")
        return f"<html><body><h2>Error creating hierarchical layout: {e}</h2></body></html>"

def create_circular_layout(relationships: List[Dict[str, str]]) -> str:
    """Create circular layout visualization."""
    try:
        net = Network(height="600px", width="100%", bgcolor="#fafafa", directed=True)
        
        # Build graph
        graph = nx.DiGraph()
        for rel in relationships:
            graph.add_edge(rel['source'], rel['target'], relation=rel['relation'])
        
        # Calculate circular positions
        nodes = list(graph.nodes())
        n = len(nodes)
        
        if n == 0:
            return "<html><body><h2>No nodes to display</h2></body></html>"
        
        # Position nodes in a circle
        import math
        radius = 200
        for i, node in enumerate(nodes):
            angle = 2 * math.pi * i / n
            x = radius * math.cos(angle)
            y = radius * math.sin(angle)
            
            net.add_node(
                node,
                label=node,
                x=x,
                y=y,
                color='#FF9800',
                size=25,
                physics=False
            )
        
        # Add edges
        for source, target, data in graph.edges(data=True):
            net.add_edge(source, target, label=data.get('relation', ''))
        
        # Disable physics for fixed positions
        net.set_options("""
        var options = {
          "physics": {"enabled": false},
          "edges": {"smooth": {"type": "continuous"}}
        }
        """)
        
        return net.generate_html()
        
    except Exception as e:
        logger.error(f"Error creating circular layout: {e}")
        return f"<html><body><h2>Error creating circular layout: {e}</h2></body></html>"

def create_force_directed_layout(relationships: List[Dict[str, str]]) -> str:
    """Create force-directed layout (default)."""
    visualizer = KnowledgeGraphVisualizer()
    result = visualizer.create_graph_from_relationships(relationships)
    return result["html_content"]