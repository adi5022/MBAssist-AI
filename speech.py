import io
import os
import requests
from groq import Groq
from config import GROQ_API_KEY

def contains_malayalam(text: str) -> bool:
    """Return True if text contains Malayalam Unicode characters."""
    return any('\u0d00' <= char <= '\u0d7f' for char in text)

def transcribe_audio(file_bytes: bytes, filename: str = "audio.webm", language: str = "en") -> tuple[str, bool]:
    """Transcribe audio.
    If language is 'en', uses Groq Whisper.
    If language is 'ml-mix', uses Sarvam AI with mode='codemix'.
    If language is 'ml', uses Sarvam AI with mode='transcribe'.
    Returns (transcription_text, used_sarvam).
    """
    sarvam_key = os.environ.get("SARVAM_AI")

    # If Malayalam/Sarvam is selected explicitly by the user
    if language in ["ml", "ml-mix"] and sarvam_key:
        mode = "codemix" if language == "ml-mix" else "transcribe"
        print(f"[INFO] Using Sarvam AI (language: {language}, mode: {mode})...")
        try:
            url = "https://api.sarvam.ai/speech-to-text"
            headers = {"api-subscription-key": sarvam_key.strip()}
            files = {"file": (filename, file_bytes)}
            data = {
                "model": "saaras:v3",
                "mode": mode,
                "language_code": "ml-IN"
            }
            response = requests.post(url, headers=headers, files=files, data=data, timeout=15)
            if response.status_code == 200:
                sarvam_text = response.json().get("transcript", "").strip()
                if sarvam_text:
                    print(f"[OK] Sarvam AI transcription success ({mode}).")
                    return sarvam_text, True
            else:
                print(f"[WARN] Sarvam AI API returned code {response.status_code}: {response.text}")
        except Exception as se:
            print(f"[ERROR] Sarvam AI API call failed: {str(se)}")
            
    # Default fallback to Groq Whisper (for 'en' or if Sarvam failed)
    print(f"[INFO] Using Groq Whisper for transcription (selected: {language})...")
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
            return transcription.text.strip(), False
    except Exception as e:
        print(f"[ERROR] Groq Whisper transcription failed: {str(e)}")

    return "", False

