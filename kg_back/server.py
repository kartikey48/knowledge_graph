from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

# Semantic Scholar base URL
BASE_URL = "https://api.semanticscholar.org/graph/v1"

@app.route('/')
def home():
    return "Semantic Scholar API Backend is running!"

@app.route('/api/search', methods=['GET'])
def search_papers():
    query = request.args.get('query')
    if not query:
        return jsonify({"error": "Query parameter is required"}), 400

    # Define fields you want in the response
    fields = "title,authors,abstract,year,venue,url"

    try:
        # Send request to Semantic Scholar API
        response = requests.get(
            f"{BASE_URL}/paper/search",
            params={"query": query, "limit": 5, "fields": fields}
        )
        response.raise_for_status()
        data = response.json()

        # Return the papers found
        return jsonify(data)

    except requests.exceptions.RequestException as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
