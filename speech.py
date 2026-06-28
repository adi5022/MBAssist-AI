import io
import os
import requests
from groq import Groq
from config import GROQ_API_KEY

def contains_malayalam(text: str) -> bool:
    """Return True if text contains Malayalam Unicode characters."""
    return any('\u0d00' <= char <= '\u0d7f' for char in text)

def transcribe_audio(file_bytes: bytes, filename: str = "audio.webm") -> str:
    """Transcribe audio. Uses Groq Whisper first, and falls back to Sarvam AI if Malayalam is detected or Whisper fails."""
    whisper_text = ""
    
    # 1. Try Groq Whisper
    try:
        if GROQ_API_KEY:
            client = Groq(api_key=GROQ_API_KEY)
            audio_file = io.BytesIO(file_bytes)
            audio_file.name = filename
            
            transcription = client.audio.transcriptions.create(
                file=(filename, audio_file),
                model="whisper-large-v3",
                response_format="json"
            )
            whisper_text = transcription.text.strip()
    except Exception as e:
        print(f"[WARN] Groq Whisper transcription failed: {str(e)}")

    # 2. Check if we should fall back to Sarvam AI
    # Fallback if Whisper output is empty, or contains Malayalam script
    is_ml = contains_malayalam(whisper_text)
    sarvam_key = os.environ.get("SARVAM_AI")

    if (not whisper_text or is_ml) and sarvam_key:
        print(f"[INFO] Falling back to Sarvam AI (Malayalam={is_ml}, Empty={not whisper_text})...")
        try:
            url = "https://api.sarvam.ai/speech-to-text"
            headers = {"api-subscription-key": sarvam_key.strip()}
            files = {"file": (filename, file_bytes)}
            data = {"model": "saaras:v3", "mode": "transcribe"}
            
            response = requests.post(url, headers=headers, files=files, data=data, timeout=12)
            if response.status_code == 200:
                sarvam_text = response.json().get("transcript", "").strip()
                if sarvam_text:
                    print("[OK] Sarvam AI transcription success.")
                    return sarvam_text
            else:
                print(f"[WARN] Sarvam AI API returned code {response.status_code}: {response.text}")
        except Exception as se:
            print(f"[ERROR] Sarvam AI API fallback failed: {str(se)}")

    return whisper_text

