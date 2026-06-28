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

@app.route("/api/transcribe", methods=["POST"])
def transcribe():
    """API endpoint to transcribe uploaded audio files using Groq Whisper API."""
    try:
        if "audio" not in request.files:
            return jsonify({"error": "No audio file provided."}), 400
            
        audio_file = request.files["audio"]
        if audio_file.filename == "":
            return jsonify({"error": "Invalid audio file."}), 400
            
        file_bytes = audio_file.read()
        if not file_bytes:
            return jsonify({"error": "Audio file is empty."}), 400
            
        from speech import transcribe_audio
        text = transcribe_audio(file_bytes, audio_file.filename)
        return jsonify({"text": text})
        
    except Exception as e:
        print(f"[ERROR] Error in /api/transcribe: {str(e)}", file=sys.stderr)
        return jsonify({"error": f"Transcription failed: {str(e)}"}), 500

@app.route("/api/sarvam-usage", methods=["GET"])
def sarvam_usage():
    """Fetch remaining credits from Sarvam AI API usage endpoint."""
    try:
        import requests
        sarvam_key = os.environ.get("SARVAM_AI")
        if not sarvam_key:
            return jsonify({"error": "Sarvam key not set"}), 404
            
        url = "https://api.sarvam.ai/usage"
        headers = {"api-subscription-key": sarvam_key.strip()}
        response = requests.get(url, headers=headers, timeout=5)
        
        if response.status_code == 200:
            return jsonify(response.json())
        else:
            return jsonify({"error": f"Sarvam API status {response.status_code}"}), response.status_code
    except Exception as e:
        return jsonify({"error": str(e)}), 500

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
