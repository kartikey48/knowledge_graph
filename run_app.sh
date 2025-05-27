#!/bin/bash

# Knowledge Graph Application Startup Script

echo "Starting Knowledge Graph Application..."

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed"
    exit 1
fi

# Check if pip is installed
if ! command -v pip3 &> /dev/null; then
    echo "Error: pip3 is not installed"
    exit 1
fi

# Install dependencies
echo "Installing Python dependencies..."
pip3 install -r requirements.txt

# Check if Ollama is installed
if ! command -v ollama &> /dev/null; then
    echo "Warning: Ollama is not installed. Text extraction may not work."
    echo "Install Ollama from: https://ollama.ai"
else
    echo "Checking Ollama models..."
    # Try to pull mistral model if not available
    ollama pull mistral:7b 2>/dev/null || echo "Note: Mistral model not available, will try other models"
fi

# Create necessary directories
mkdir -p uploaded_pdfs
mkdir -p logs

# Start the FastAPI backend
echo "Starting FastAPI backend on port 8000..."
python3 -m uvicorn backend.app:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!

# Wait a moment for backend to start
sleep 3

# Check if backend is running
if ps -p $BACKEND_PID > /dev/null; then
    echo "Backend started successfully (PID: $BACKEND_PID)"
    echo ""
    echo "Application is now running!"
    echo "- Backend API: http://localhost:8000"
    echo "- API Documentation: http://localhost:8000/docs"
    echo "- Graph Viewer: Open frontend/graph_viewer.html in your browser"
    echo ""
    echo "Press Ctrl+C to stop the application"
    
    # Keep script running and handle cleanup
    trap "echo 'Stopping application...'; kill $BACKEND_PID; exit 0" INT
    wait $BACKEND_PID
else
    echo "Error: Failed to start backend"
    exit 1
fi
