import pickle
import numpy as np
import faiss
import fitz  # PyMuPDF
from pathlib import Path
from sentence_transformers import SentenceTransformer

from config import PDF_PATH, CACHE_FILE, CHUNK_SIZE, CHUNK_STEP, TOP_K

def extract_pdf_text(path: Path) -> list[dict]:
    """Extract text from every page of the PDF using PyMuPDF.
    Returns a list of {page, text} dicts."""
    if not path.exists():
        raise FileNotFoundError(f"PDF file not found at: {path.absolute()}")
    doc = fitz.open(str(path))
    pages = []
    for i, page in enumerate(doc):
        text = page.get_text("text").strip()
        if text:
            pages.append({"page": i + 1, "text": text})
    doc.close()
    print(f"[OK] Extracted text from {len(pages)} pages")
    return pages

def chunk_pages(pages: list[dict], size: int = CHUNK_SIZE,
                step: int = CHUNK_STEP) -> tuple[list[str], list[dict]]:
    """Sliding-window word chunker. Returns (chunks, metadata)."""
    chunks, meta = [], []
    for page_info in pages:
        words = page_info["text"].split()
        page_num = page_info["page"]
        for i in range(0, len(words), step):
            chunk = " ".join(words[i : i + size])
            if len(chunk.strip()) < 60:
                continue
            chunks.append(chunk)
            meta.append({"page": page_num, "offset": i})
    print(f"[OK] Created {len(chunks):,} chunks (size={size}, step={step})")
    return chunks, meta

class FAISSStore:
    """Sentence Transformers -> Dense vectors -> FAISS IndexFlatIP (cosine similarity)."""

    def __init__(self, chunks: list[str] = None, meta: list[dict] = None,
                 cache: Path = CACHE_FILE, model_name: str = "all-MiniLM-L6-v2"):
        self.cache = cache
        self.model_name = model_name
        
        # Load embedding model
        print(f"[INFO] Initialising SentenceTransformer model: {model_name}...")
        self.model = SentenceTransformer(model_name)
        
        if cache.exists():
            print("[INFO] Loading FAISS index from cache ...")
            with open(cache, "rb") as f:
                data = pickle.load(f)
            self.chunks     = data["chunks"]
            self.meta       = data["meta"]
            self.dim        = data["dim"]
            vecs            = data["vectors"]
            self.index      = faiss.IndexFlatIP(self.dim)
            self.index.add(vecs)
        else:
            if chunks is None or meta is None:
                raise ValueError("Chunks and metadata must be provided to build FAISS store from scratch.")
            self._build(chunks, meta, cache)
        print(f"[OK] FAISS ready — {self.index.ntotal:,} vectors, dim={self.dim}")

    def _build(self, chunks, meta, cache):
        print("[BUILD] Generating dense embeddings using SentenceTransformer ...")
        self.chunks     = chunks
        self.meta       = meta
        
        # Generate embeddings
        embeddings = self.model.encode(chunks, show_progress_bar=True)
        embeddings = np.array(embeddings).astype(np.float32)
        
        # Normalize vectors for Cosine Similarity (using IndexFlatIP)
        faiss.normalize_L2(embeddings)
        
        self.dim = embeddings.shape[1]
        self.index = faiss.IndexFlatIP(self.dim)
        self.index.add(embeddings)

        # Ensure parent folder exists
        cache.parent.mkdir(parents=True, exist_ok=True)
        with open(cache, "wb") as f:
            pickle.dump({
                "dim": self.dim, "chunks": self.chunks,
                "meta": self.meta, "vectors": embeddings,
            }, f)
        print("[OK] Index built & cached")

    def _embed(self, text: str) -> np.ndarray:
        x = self.model.encode([text]).astype(np.float32)
        faiss.normalize_L2(x)
        return x

    def search(self, query: str, k: int = TOP_K) -> list[dict]:
        scores, idxs = self.index.search(self._embed(query), k)
        return [
            {
                "text":   self.chunks[i],
                "score":  float(scores[0][r]),
                "page":   self.meta[i]["page"],
            }
            for r, i in enumerate(idxs[0]) if i != -1
        ]

# Global singleton or helper to get the initialized vector store
_vector_store = None

def get_vector_store():
    global _vector_store
    if _vector_store is not None:
        return _vector_store

    if CACHE_FILE.exists():
        _vector_store = FAISSStore(cache=CACHE_FILE)
    else:
        if not PDF_PATH.exists():
            raise FileNotFoundError(
                f"Admissions prospectus PDF not found at {PDF_PATH.absolute()} "
                f"and no FAISS cache exists at {CACHE_FILE.absolute()}. "
                f"Please place the prospectus PDF in the data/ folder."
            )
        print(f"[BUILD] Building vector index from prospectus {PDF_PATH.name}...")
        pages = extract_pdf_text(PDF_PATH)
        chunks, meta = chunk_pages(pages)
        _vector_store = FAISSStore(chunks, meta, cache=CACHE_FILE)
        
    return _vector_store
