import os
import sys
from flask import Flask, request, jsonify, render_template

from config import PDF_PATH, CACHE_FILE
from rag import ask_chatbot

# Initialize Flask application with explicit static and templates folders
app = Flask(__name__,
            static_folder="static",
            template_folder="templates")

@app.route("/")
def home():
    """Serve the admissions chatbot HTML page."""
    return render_template("index.html")

@app.route("/api/chat", methods=["POST"])
def chat():
    """API endpoint to process user messages using the LangGraph RAG pipeline."""
    try:
        data = request.get_json() or {}
        user_message = data.get("message", "").strip()

        if not user_message:
            return jsonify({"error": "Message content cannot be empty."}), 400

        # Invoke the LangGraph workflow pipeline
        result = ask_chatbot(user_message)
        
        # Extract unique page numbers from retrieved documents
        pages = []
        if result.get("action") == "retrieve" and result.get("docs"):
            pages = [doc.get("page") for doc in result.get("docs") if doc.get("page")]
        
        return jsonify({
            "answer": result.get("answer", "No answer was generated."),
            "action": result.get("action"),
            "lang_code": result.get("lang_code"),
            "lang_name": result.get("lang_name"),
            "pages": sorted(list(set(pages)))
        })

    except Exception as e:
        print(f"[ERROR] Error in /api/chat: {str(e)}", file=sys.stderr)
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500

def check_files():
    """Verify at startup that data or cache dependencies are in place."""
    print("*" * 60)
    if CACHE_FILE.exists():
        print(f"[OK] Found FAISS cache index: {CACHE_FILE.name}")
    elif PDF_PATH.exists():
        print(f"[OK] Found admissions prospectus: {PDF_PATH.name}")
        print("   The FAISS index will be built from scratch on the first query.")
    else:
        print(f"[WARN] Notice: Neither FAISS cache ({CACHE_FILE}) nor PDF prospectus ({PDF_PATH}) was found.")
        print("   Please place 'mbcet_prospectus.pdf' in the 'data/' directory before querying.")
    print("*" * 60)

if __name__ == "__main__":
    check_files()
    # Run the Flask development server locally on port 5000
    app.run(host="127.0.0.1", port=5000, debug=True)
