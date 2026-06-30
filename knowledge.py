import pickle
import numpy as np
import faiss
import fitz  # PyMuPDF
from pathlib import Path
from sentence_transformers import SentenceTransformer
from sklearn.feature_extraction.text import TfidfVectorizer

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
    """Hybrid Search: Sentence Transformers (Dense) + TF-IDF (Sparse) with RRF merging."""

    def __init__(self, chunks: list[str] = None, meta: list[dict] = None,
                 cache: Path = CACHE_FILE, model_name: str = "all-MiniLM-L6-v2"):
        self.cache = cache
        self.model_name = model_name
        
        # Load embedding model
        print(f"[INFO] Initialising SentenceTransformer model: {model_name}...")
        self.model = SentenceTransformer(model_name)
        
        if cache.exists():
            print("[INFO] Loading hybrid FAISS index from cache ...")
            with open(cache, "rb") as f:
                data = pickle.load(f)
            self.chunks           = data["chunks"]
            self.meta             = data["meta"]
            self.dim              = data["dim"]
            self.tfidf_vectorizer = data["tfidf_vectorizer"]
            self.tfidf_matrix     = data["tfidf_matrix"]
            vecs                  = data["vectors"]
            
            self.index = faiss.IndexFlatIP(self.dim)
            self.index.add(vecs)
        else:
            if chunks is None or meta is None:
                raise ValueError("Chunks and metadata must be provided to build FAISS store from scratch.")
            self._build(chunks, meta, cache)
        print(f"[OK] Hybrid FAISS ready — {self.index.ntotal:,} vectors, dim={self.dim}")

    def _build(self, chunks, meta, cache):
        print("[BUILD] Generating dense embeddings using SentenceTransformer ...")
        self.chunks = chunks
        self.meta   = meta
        
        # 1. Dense Embeddings
        embeddings = self.model.encode(chunks, show_progress_bar=True)
        embeddings = np.array(embeddings).astype(np.float32)
        faiss.normalize_L2(embeddings)
        self.dim = embeddings.shape[1]
        
        self.index = faiss.IndexFlatIP(self.dim)
        self.index.add(embeddings)
        
        # 2. Sparse TF-IDF fitting
        print("[BUILD] Fitting TF-IDF vectorizer ...")
        self.tfidf_vectorizer = TfidfVectorizer(
            max_features=80_000, ngram_range=(1, 2), sublinear_tf=True
        )
        self.tfidf_matrix = self.tfidf_vectorizer.fit_transform(chunks)

        # Cache it
        cache.parent.mkdir(parents=True, exist_ok=True)
        with open(cache, "wb") as f:
            pickle.dump({
                "dim": self.dim,
                "chunks": self.chunks,
                "meta": self.meta,
                "vectors": embeddings,
                "tfidf_vectorizer": self.tfidf_vectorizer,
                "tfidf_matrix": self.tfidf_matrix,
            }, f)
        print("[OK] Hybrid Index built & cached")

    def search(self, query: str, k: int = TOP_K) -> list[dict]:
        candidate_pool_size = max(k * 3, 20)
        
        # ─── 1. Dense Search ───
        query_dense = self.model.encode([query]).astype(np.float32)
        faiss.normalize_L2(query_dense)
        dense_scores, dense_idxs = self.index.search(query_dense, candidate_pool_size)
        
        dense_results = {}
        for rank, idx in enumerate(dense_idxs[0]):
            if idx != -1:
                dense_results[idx] = rank + 1
                
        # ─── 2. Sparse Search ───
        query_sparse = self.tfidf_vectorizer.transform([query])
        sparse_similarities = self.tfidf_matrix.dot(query_sparse.T).toarray().ravel()
        sparse_idxs = np.argsort(sparse_similarities)[::-1][:candidate_pool_size]
        
        sparse_results = {}
        for rank, idx in enumerate(sparse_idxs):
            if sparse_similarities[idx] > 0:
                sparse_results[idx] = rank + 1

        # ─── 3. Reciprocal Rank Fusion (RRF) Merge ───
        all_candidates = set(dense_results.keys()).union(set(sparse_results.keys()))
        rrf_scores = {}
        
        for idx in all_candidates:
            score = 0.0
            if idx in dense_results:
                score += 1.0 / (60.0 + dense_results[idx])
            if idx in sparse_results:
                score += 1.0 / (60.0 + sparse_results[idx])
            rrf_scores[idx] = score
            
        sorted_candidates = sorted(rrf_scores.items(), key=lambda item: item[1], reverse=True)[:k]
        
        return [
            {
                "text":  self.chunks[idx],
                "score": float(rrf_scores[idx]),
                "page":  self.meta[idx]["page"],
            }
            for idx, rrf_score in sorted_candidates
        ]

def chunk_web_pages(pages: list[dict], size: int = CHUNK_SIZE,
                    step: int = CHUNK_STEP) -> tuple[list[str], list[dict]]:
    """Sliding-window word chunker for web pages. Returns (chunks, metadata)."""
    chunks, meta = [], []
    for page_info in pages:
        words = page_info["text"].split()
        url = page_info["url"]
        title = page_info.get("title", "Web Page")
        for i in range(0, len(words), step):
            chunk = " ".join(words[i : i + size])
            if len(chunk.strip()) < 60:
                continue
            chunks.append(chunk)
            meta.append({"page": f"URL: {url}", "offset": i, "title": title})
    print(f"[OK] Created {len(chunks):,} web chunks (size={size}, step={step})")
    return chunks, meta

def rebuild_unified_index(crawled_pages: list[dict]):
    """Rebuilds the hybrid FAISS index combining PDF prospectus and crawled web pages."""
    global _vector_store
    pdf_chunks, pdf_meta = [], []
    if PDF_PATH.exists():
        print(f"[BUILD] Extracting text from prospectus {PDF_PATH.name}...")
        pdf_pages = extract_pdf_text(PDF_PATH)
        pdf_chunks, pdf_meta = chunk_pages(pdf_pages)
    else:
        print(f"[WARN] Admissions prospectus PDF not found at {PDF_PATH.absolute()}")
        
    web_chunks, web_meta = chunk_web_pages(crawled_pages)
    
    all_chunks = pdf_chunks + web_chunks
    all_meta = pdf_meta + web_meta
    
    if not all_chunks:
        raise ValueError("No text extracted from PDF or web pages. Cannot build index.")
        
    print(f"[BUILD] Rebuilding unified FAISS store with {len(all_chunks)} chunks...")
    
    # Clean cache file if it exists to ensure rebuild from scratch
    if CACHE_FILE.exists():
        try:
            CACHE_FILE.unlink()
        except Exception as e:
            print(f"[WARN] Failed to delete cache file before rebuild: {e}")

    _vector_store = FAISSStore(all_chunks, all_meta, cache=CACHE_FILE)
    return _vector_store

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
