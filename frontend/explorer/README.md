# Knowledge Graph Explorer

A static companion to the original FastAPI and Ollama project. It builds graphs in the browser from selectable PDF text or pasted text. Generated relationships count shared passages. The built-in example uses a subset of the repository's health equity graph.

## Run locally

From this directory, run `python -m http.server 8080` and open http://localhost:8080. A static web server is required for module imports, the PDF worker and sample data. To deploy elsewhere, publish this directory as the site root.

The explorer processes up to 120,000 characters per source. PDFs must be 20 MB or smaller and no longer than 100 pages. Scanned PDFs need OCR before use.

The existing repository's FastAPI and Ollama workflow remains available for model-based semantic relationship extraction. This browser edition uses passage co-occurrence and exports nodes and edges as JSON.

## Assets

The vis-network bundle comes from the original repository and includes its license notice. PDF.js 4.10.38 is bundled with its Apache license. The sample is derived from `data_output/OrfPathHealth/graph.csv` in the original repository.
