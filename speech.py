import io
from groq import Groq
from config import GROQ_API_KEY

def transcribe_audio(file_bytes: bytes, filename: str = "audio.webm") -> str:
    """Send audio bytes to Groq Whisper API for transcription."""
    if not GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY is not set in environment variables.")
        
    client = Groq(api_key=GROQ_API_KEY)
    
    # Wrap bytes in a file-like BytesIO stream
    audio_file = io.BytesIO(file_bytes)
    audio_file.name = filename
    
    transcription = client.audio.transcriptions.create(
        file=(filename, audio_file),
        model="whisper-large-v3",
        response_format="json"
    )
    return transcription.text
