# Knowledge Graph Generator

A comprehensive web application that converts PDF documents into interactive knowledge graphs using AI-powered concept extraction and relationship mapping.

![Knowledge Graph Banner](./assets/KG_banner.png)

## 🌟 Features

- **PDF Processing**: Upload and extract text from PDF documents
- **AI-Powered Extraction**: Uses Ollama/Mistral for concept and relationship extraction
- **Interactive Visualization**: Multiple graph layouts (force-directed, hierarchical, circular)
- **Academic Integration**: Search related papers via Semantic Scholar API
- **Export Capabilities**: Download graphs as HTML or PNG images
- **Real-time Processing**: Asynchronous processing with progress indicators
- **Responsive Design**: Works on desktop and mobile devices

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │    Backend      │    │   External      │
│   (HTML/JS)     │◄──►│   (FastAPI)     │◄──►│   Services      │
│                 │    │                 │    │                 │
│ • File Upload   │    │ • PDF Parser    │    │ • Ollama/LLM    │
│ • Graph Viewer  │    │ • Graph Builder │    │ • Semantic      │
│ • Controls      │    │ • API Endpoints │    │   Scholar       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- Docker (optional)
- Ollama installed and running

### Option 1: Docker Compose (Recommended)

```bash
# Clone the repository
git clone https://github.com/kartikey48/knowledge_graph.git
cd knowledge_graph

# Start all services
docker-compose up -d

# Access the application
open http://localhost:3000
```

### Option 2: Manual Setup

#### Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start Ollama (in separate terminal)
ollama serve
ollama pull mistral:7b

# Start backend
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

#### Frontend Setup

```bash
# Open the HTML file directly in browser
open frontend/graph_viewer.html

# Or serve with a simple HTTP server
cd frontend
python -m http.server 8080
open http://localhost:8080/graph_viewer.html
```

## 📖 Usage

### 1. Upload PDF Document

1. Open the web interface
2. Click "Select PDF Document" or drag & drop a PDF file
3. Choose your preferred graph layout
4. Click "Generate Knowledge Graph"

### 2. View Results

- **Metadata Panel**: Shows document statistics and extraction results
- **Interactive Graph**: Explore concepts and relationships
- **Graph Controls**: Fit to screen, toggle physics, export options

### 3. Export Options

- **Download HTML**: Get standalone HTML file with the graph
- **Export PNG**: Save graph as image
- **View Source Data**: Access raw relationship data

## 🔧 API Endpoints

### Core Endpoints

```http
POST /upload
Content-Type: multipart/form-data

Upload PDF and generate knowledge graph
```

```http
GET /query?node={concept}&domain={field}

Search related papers by concept and domain
```

```http
GET /author?name={author_name}

Get papers by author name
```

### Response Format

```json
{
  "metadata": {
    "filename": "document.pdf",
    "text_length": 15420,
    "num_relationships": 25,
    "num_nodes": 18,
    "num_edges": 25
  },
  "graph": [
    {
      "data": {
        "id": "Machine Learning",
        "label": "Machine Learning",
        "type": "concept"
      }
    },
    {
      "data": {
        "id": "edge1",
        "source": "Machine Learning",
        "target": "Neural Networks",
        "label": "uses",
        "type": "relationship"
      }
    }
  ]
}
```

## ⚙️ Configuration

### Backend Configuration

Edit `backend/config.py`:

```python
# File upload settings
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
ALLOWED_EXTENSIONS = {".pdf"}

# Ollama settings
OLLAMA_MODELS = ["mistral:7b", "mistral", "llama2"]
OLLAMA_TIMEOUT = 30

# Graph processing
MAX_RELATIONSHIPS = 10
MAX_TEXT_LENGTH = 1500
```

### Environment Variables

```bash
# Development
export ENVIRONMENT=development
export LOG_LEVEL=DEBUG

# Production
export ENVIRONMENT=production
export LOG_LEVEL=WARNING
export API_HOST=0.0.0.0
```

## 🧪 Testing

### Backend Tests

```bash
cd backend

# Run basic extraction test
python extractor.py

# Test Semantic Scholar API
python helpers/semantic_scholar.py

# Test full pipeline
python -m pytest tests/ -v
```

### Frontend Testing

```bash
# Test with sample PDF
curl -X POST "http://localhost:8000/upload" \
  -F "file=@sample.pdf" \
  -F "layout=force"
```

## 🔍 Troubleshooting

### Common Issues

1. **Ollama Connection Error**
   ```bash
   # Check if Ollama is running
   ps aux | grep ollama
   
   # Start Ollama
   ollama serve
   
   # Pull required model
   ollama pull mistral:7b
   ```

2. **PDF Processing Fails**
   - Ensure PDF contains readable text (not just images)
   - Check file size (max 50MB)
   - Verify PDF is not password protected

3. **Graph Not Displaying**
   - Check browser console for errors
   - Ensure backend is running on port 8000
   - Verify CORS settings

4. **No Relationships Extracted**
   - Document may be too short or lack technical content
   - Try with academic papers or technical documents
   - Check Ollama model availability

### Debug Mode

```bash
# Enable debug logging
export LOG_LEVEL=DEBUG

# Check logs
tail -f backend/logs/api.log
```

## 🛠️ Development

### Project Structure

```
knowledge_graph/
├── backend/
│   ├── app.py                 # FastAPI application
│   ├── extractor.py           # Core extraction logic
│   ├── graph_visualizer.py    # Graph visualization
│   ├── config.py              # Configuration
│   ├── helpers/
│   │   ├── pdf_parser.py      # PDF processing
│   │   └── semantic_scholar.py # Academic search
│   └── requirements.txt
├── frontend/
│   ├── graph_viewer.html      # Main interface
│   └── nginx.conf
├── docker-compose.yml
└── README.md
```

### Adding New Features

1. **New Extraction Methods**
   - Extend `extractor.py