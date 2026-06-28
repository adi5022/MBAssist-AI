import pickle
import numpy as np
import faiss
import fitz  # PyMuPDF
from pathlib import Path
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer

from config import PDF_PATH, CACHE_FILE, CHUNK_SIZE, CHUNK_STEP, EMBED_DIM, TOP_K

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
    """TF-IDF + LSA -> L2-normalised dense vectors -> FAISS IndexFlatIP (cosine)."""

    def __init__(self, chunks: list[str] = None, meta: list[dict] = None,
                 cache: Path = CACHE_FILE, dim: int = EMBED_DIM):
        self.cache = cache
        self.dim = dim
        if cache.exists():
            print("[INFO] Loading FAISS index from cache ...")
            with open(cache, "rb") as f:
                data = pickle.load(f)
            self.vectorizer = data["vectorizer"]
            self.svd        = data["svd"]
            self.dim        = data["dim"]
            self.chunks     = data["chunks"]
            self.meta       = data["meta"]
            vecs            = data["vectors"]
            self.index      = faiss.IndexFlatIP(self.dim)
            self.index.add(vecs)
        else:
            if chunks is None or meta is None:
                raise ValueError("Chunks and metadata must be provided to build FAISS store from scratch.")
            self._build(chunks, meta, cache, dim)
        print(f"[OK] FAISS ready — {self.index.ntotal:,} vectors, dim={self.dim}")

    def _build(self, chunks, meta, cache, dim):
        print("[BUILD] Fitting TF-IDF ...")
        self.chunks     = chunks
        self.meta       = meta
        self.vectorizer = TfidfVectorizer(
            max_features=80_000, ngram_range=(1, 2), sublinear_tf=True
        )
        X_sp = self.vectorizer.fit_transform(chunks)

        real_dim    = min(dim, X_sp.shape[1] - 1, X_sp.shape[0] - 1)
        self.dim    = real_dim
        print(f"[BUILD] Fitting LSA (dim={real_dim}) ...")
        self.svd    = TruncatedSVD(n_components=real_dim, random_state=42)
        X_dense     = self.svd.fit_transform(X_sp).astype(np.float32)
        faiss.normalize_L2(X_dense)

        self.index  = faiss.IndexFlatIP(real_dim)
        self.index.add(X_dense)

        # Ensure parent folder exists
        cache.parent.mkdir(parents=True, exist_ok=True)
        with open(cache, "wb") as f:
            pickle.dump({
                "vectorizer": self.vectorizer, "svd": self.svd,
                "dim": self.dim, "chunks": self.chunks,
                "meta": self.meta, "vectors": X_dense,
            }, f)
        print("[OK] Index built & cached")

    def _embed(self, text: str) -> np.ndarray:
        x = self.svd.transform(
            self.vectorizer.transform([text])
        ).astype(np.float32)
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
