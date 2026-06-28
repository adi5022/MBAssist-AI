import os
from pathlib import Path
from dotenv import load_dotenv

# Load local environment variables from .env file if present
load_dotenv()

# Directories
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
CACHE_DIR = BASE_DIR / "cache"

# Ensure directories exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# Default path configs
PDF_PATH = DATA_DIR / "mbcet_prospectus.pdf"
CACHE_FILE = CACHE_DIR / "mbcet_faiss.pkl"

# Hyperparameters / Configurations
CHUNK_SIZE = 350    # words per chunk
CHUNK_STEP = 150    # stride (overlap ~57 %)
EMBED_DIM = 256     # LSA dimensions
TOP_K = 5           # passages per query

GROQ_MODEL = "llama-3.3-70b-versatile"
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

# Supported Languages
LANGUAGE_NAMES = {
    "en": "English",    "ml": "Malayalam",  "hi": "Hindi",
    "ta": "Tamil",      "te": "Telugu",     "kn": "Kannada",
    "fr": "French",     "de": "German",     "es": "Spanish",
    "zh-cn": "Chinese", "ar": "Arabic",     "ja": "Japanese",
}
