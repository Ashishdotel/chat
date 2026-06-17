"""
rag_service.py — RAG Ingestion & Retrieval Pipeline
-----------------------------------------------------
This module implements the full RAG pipeline in two stages:

STAGE 1 — INGESTION (run once per document):
  PDF file → extract text → split into chunks →
  embed each chunk via OpenAI → store in FAISS index

STAGE 2 — RETRIEVAL (run on every user query):
  User query → embed query → FAISS similarity search →
  return top-K most relevant text chunks

Why FAISS?
- Runs entirely locally — no external vector DB server needed
- Fast even with thousands of chunks
- Persists to disk as two files (index.faiss + metadata.json)
- Ideal for a thesis project: simple, auditable, reproducible

Why text-embedding-3-small?
- Cheapest OpenAI embedding model
- 1536-dimensional vectors
- Excellent performance on multilingual text including Nepali

Chunking strategy:
- Fixed-size token windows with overlap
- Overlap prevents losing context at chunk boundaries
  (e.g. a sentence that spans two chunks is partially in both)
"""

import os
import json
import time
import numpy as np
import faiss
import tiktoken
from pypdf import PdfReader
from typing import List, Dict, Tuple, Optional

from backend.config import settings
from backend.utils.logger import get_logger

logger = get_logger(__name__)

# RAG embeddings still use OpenAI text-embedding model if available.
# If no OpenAI key is configured, RAG is disabled gracefully.
try:
    from openai import OpenAI as _OpenAI
    _openai_key = getattr(settings, "openai_api_key", None)
    client = _OpenAI(api_key=_openai_key) if _openai_key else None
except Exception:
    client = None

# ── Paths ─────────────────────────────────────────────────────────────────────
FAISS_INDEX_PATH    = os.path.join(settings.vector_store_dir, "index.faiss")
METADATA_PATH       = os.path.join(settings.vector_store_dir, "metadata.json")
DOCUMENTS_LIST_PATH = os.path.join(settings.vector_store_dir, "documents.json")

# ── Tokeniser (for accurate chunk sizing) ─────────────────────────────────────
# cl100k_base is the tokeniser used by GPT-4 and text-embedding-3 models
_tokeniser = tiktoken.get_encoding("cl100k_base")


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def _ensure_dirs():
    """Creates required directories if they don't exist."""
    os.makedirs(settings.documents_dir,   exist_ok=True)
    os.makedirs(settings.vector_store_dir, exist_ok=True)


def _count_tokens(text: str) -> int:
    """Returns the number of tokens in a text string."""
    return len(_tokeniser.encode(text))


def _load_metadata() -> List[Dict]:
    """
    Loads chunk metadata from disk.

    Metadata is a JSON list where each entry corresponds to one
    FAISS vector and contains:
      - text:        the raw chunk text
      - source:      original PDF filename
      - chunk_index: position of this chunk in the document
      - page:        PDF page number (0-indexed)
    """
    if not os.path.exists(METADATA_PATH):
        return []
    with open(METADATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_metadata(metadata: List[Dict]):
    """Saves chunk metadata list to disk as JSON."""
    _ensure_dirs()
    with open(METADATA_PATH, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)


def _load_documents_list() -> List[Dict]:
    """
    Loads the list of indexed documents.
    Each entry: {filename, page_count, chunk_count, indexed_at}
    """
    if not os.path.exists(DOCUMENTS_LIST_PATH):
        return []
    with open(DOCUMENTS_LIST_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_documents_list(docs: List[Dict]):
    """Saves the indexed documents list to disk."""
    _ensure_dirs()
    with open(DOCUMENTS_LIST_PATH, "w", encoding="utf-8") as f:
        json.dump(docs, f, ensure_ascii=False, indent=2)


def _load_faiss_index() -> Optional[faiss.IndexFlatIP]:
    """
    Loads the FAISS index from disk.

    IndexFlatIP uses Inner Product (dot product) similarity.
    With normalised vectors, this is equivalent to cosine similarity,
    which is the standard for comparing text embeddings.

    Returns None if no index exists yet.
    """
    if not os.path.exists(FAISS_INDEX_PATH):
        return None
    index = faiss.read_index(FAISS_INDEX_PATH)
    logger.debug(f"FAISS index loaded: {index.ntotal} vectors")
    return index


def _save_faiss_index(index: faiss.IndexFlatIP):
    """Saves the FAISS index to disk."""
    _ensure_dirs()
    faiss.write_index(index, FAISS_INDEX_PATH)
    logger.debug(f"FAISS index saved: {index.ntotal} vectors")


# =============================================================================
# STAGE 1A: PDF TEXT EXTRACTION
# =============================================================================

def extract_text_from_pdf(pdf_path: str) -> List[Dict]:
    """
    Extracts text from every page of a PDF file.

    Args:
        pdf_path: Absolute path to the PDF file

    Returns:
        List of dicts: [{"page": 0, "text": "..."}, ...]
        Pages with no extractable text are skipped.
    """
    logger.info(f"Extracting text from: {os.path.basename(pdf_path)}")
    pages = []

    try:
        reader = PdfReader(pdf_path)
        total_pages = len(reader.pages)
        logger.info(f"PDF has {total_pages} pages")

        for page_num, page in enumerate(reader.pages):
            text = page.extract_text()

            # Skip pages with no extractable text (scanned images, etc.)
            if not text or not text.strip():
                logger.debug(f"Page {page_num + 1}: no extractable text, skipping")
                continue

            # Normalise whitespace
            cleaned = " ".join(text.split())
            pages.append({"page": page_num, "text": cleaned})
            logger.debug(f"Page {page_num + 1}: {_count_tokens(cleaned)} tokens extracted")

    except Exception as e:
        logger.error(f"PDF extraction failed: {str(e)}")
        raise

    logger.info(f"Extracted text from {len(pages)} pages")
    return pages


# =============================================================================
# STAGE 1B: TEXT CHUNKING
# =============================================================================

def chunk_pages(pages: List[Dict], source_filename: str) -> List[Dict]:
    """
    Splits page text into overlapping fixed-size token chunks.

    Why overlap?
    If a sentence is split at a chunk boundary, the overlap ensures
    both chunks contain partial context of that sentence.
    This prevents losing information at the edges.

    Example with chunk_size=10, overlap=3:
      tokens: [1,2,3,4,5,6,7,8,9,10,11,12,13]
      chunk1: [1,2,3,4,5,6,7,8,9,10]
      chunk2: [8,9,10,11,12,13]      ← starts 3 tokens before chunk1 ends

    Args:
        pages:           List of {page, text} dicts from extract_text_from_pdf()
        source_filename: PDF filename (stored in metadata for attribution)

    Returns:
        List of chunk dicts ready for embedding
    """
    chunk_size    = settings.rag_chunk_size
    chunk_overlap = settings.rag_chunk_overlap
    chunks        = []
    chunk_index   = 0

    for page_data in pages:
        page_num = page_data["page"]
        text     = page_data["text"]
        tokens   = _tokeniser.encode(text)

        # Slide a window of `chunk_size` tokens across this page
        start = 0
        while start < len(tokens):
            end        = min(start + chunk_size, len(tokens))
            chunk_toks = tokens[start:end]
            chunk_text = _tokeniser.decode(chunk_toks)

            chunks.append({
                "text":        chunk_text,
                "source":      source_filename,
                "chunk_index": chunk_index,
                "page":        page_num,
                "token_count": len(chunk_toks),
            })
            chunk_index += 1

            # Move window forward by (chunk_size - overlap)
            # so the next chunk starts `overlap` tokens before this one ends
            if end == len(tokens):
                break
            start += chunk_size - chunk_overlap

    logger.info(
        f"Chunking complete: {len(chunks)} chunks "
        f"(size={chunk_size}, overlap={chunk_overlap})"
    )
    return chunks


# =============================================================================
# STAGE 1C: EMBEDDING
# =============================================================================

def embed_texts(texts: List[str], batch_size: int = 100) -> np.ndarray:
    """
    Converts a list of text strings into embedding vectors using OpenAI.

    Batching:
    OpenAI's embedding API supports up to 2048 inputs per request.
    We use batch_size=100 to stay well within limits and avoid timeouts.

    Normalisation:
    We L2-normalise each vector so that inner product = cosine similarity.
    This is important for FAISS IndexFlatIP to work correctly as cosine search.

    Args:
        texts:      List of text strings to embed
        batch_size: Number of texts to send per API call

    Returns:
        numpy array of shape (len(texts), embedding_dim) — float32
    """
    all_embeddings = []
    total_batches  = (len(texts) + batch_size - 1) // batch_size

    logger.info(
        f"Embedding {len(texts)} chunks in {total_batches} batches "
        f"using {settings.rag_embedding_model}"
    )

    for i in range(0, len(texts), batch_size):
        batch     = texts[i : i + batch_size]
        batch_num = (i // batch_size) + 1

        logger.debug(f"Embedding batch {batch_num}/{total_batches} ({len(batch)} texts)")

        try:
            response = client.embeddings.create(
                model=settings.rag_embedding_model,
                input=batch,
            )
            batch_embeddings = [item.embedding for item in response.data]
            all_embeddings.extend(batch_embeddings)

            # Small delay between batches to respect rate limits
            if batch_num < total_batches:
                time.sleep(0.1)

        except Exception as e:
            logger.error(f"Embedding batch {batch_num} failed: {str(e)}")
            raise

    # Convert to float32 numpy array (required by FAISS)
    vectors = np.array(all_embeddings, dtype=np.float32)

    # L2 normalise: each vector divided by its magnitude
    # After normalisation: ||v|| = 1, so dot(v1, v2) = cos(angle between v1, v2)
    faiss.normalize_L2(vectors)

    logger.info(
        f"Embeddings generated: shape={vectors.shape}, "
        f"dtype={vectors.dtype}"
    )
    return vectors


# =============================================================================
# STAGE 1D: INDEX BUILDING
# =============================================================================

def build_or_update_index(chunks: List[Dict], vectors: np.ndarray) -> int:
    """
    Adds new vectors to the FAISS index (creates if not exists).

    This function is ADDITIVE — calling it with a new document
    appends its vectors to the existing index rather than rebuilding.

    Args:
        chunks:  List of chunk metadata dicts
        vectors: numpy array of embeddings, shape (len(chunks), dim)

    Returns:
        Total number of vectors now in the index
    """
    embedding_dim = vectors.shape[1]   # 1536 for text-embedding-3-small

    # Load existing index or create a new one
    index = _load_faiss_index()
    if index is None:
        index = faiss.IndexFlatIP(embedding_dim)
        logger.info(f"Created new FAISS index (dim={embedding_dim})")
    else:
        logger.info(f"Updating existing FAISS index (had {index.ntotal} vectors)")

    # Load existing metadata and append new chunks
    metadata = _load_metadata()
    metadata.extend(chunks)

    # Add vectors to index
    index.add(vectors)

    # Persist both to disk
    _save_faiss_index(index)
    _save_metadata(metadata)

    logger.info(f"FAISS index now contains {index.ntotal} vectors")
    return index.ntotal


# =============================================================================
# FULL INGESTION PIPELINE (called by the route)
# =============================================================================

def ingest_pdf(pdf_path: str, filename: str) -> Dict:
    """
    Runs the full ingestion pipeline for one PDF file.

    Steps:
    1. Extract text from PDF pages
    2. Split text into overlapping chunks
    3. Embed all chunks via OpenAI
    4. Add vectors to FAISS index
    5. Record document in documents list
    6. Return summary stats

    Args:
        pdf_path: Absolute path to the saved PDF file
        filename: Original upload filename (shown to user)

    Returns:
        Dict with ingestion summary: page_count, chunk_count, total_vectors
    """
    _ensure_dirs()
    logger.info(f"=== Starting ingestion: {filename} ===")

    # Step 1: Extract text
    pages = extract_text_from_pdf(pdf_path)
    if not pages:
        raise ValueError(f"No extractable text found in {filename}. "
                         f"The PDF may be scanned (image-only).")

    # Step 2: Chunk
    chunks = chunk_pages(pages, source_filename=filename)
    if not chunks:
        raise ValueError(f"Chunking produced 0 chunks for {filename}.")

    # Step 3: Embed
    texts   = [c["text"] for c in chunks]
    vectors = embed_texts(texts)

    # Step 4: Add to FAISS index
    total_vectors = build_or_update_index(chunks, vectors)

    # Step 5: Record document
    docs = _load_documents_list()
    # Remove old entry for same filename if re-uploading
    docs = [d for d in docs if d["filename"] != filename]
    docs.append({
        "filename":    filename,
        "page_count":  len(pages),
        "chunk_count": len(chunks),
        "total_vectors_in_index": total_vectors,
        "indexed_at":  time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    })
    _save_documents_list(docs)

    result = {
        "filename":     filename,
        "page_count":   len(pages),
        "chunk_count":  len(chunks),
        "total_vectors": total_vectors,
    }
    logger.info(f"=== Ingestion complete: {result} ===")
    return result


# =============================================================================
# STAGE 2: RETRIEVAL (called on every chat message when RAG is enabled)
# =============================================================================

def retrieve_relevant_chunks(query: str, top_k: Optional[int] = None) -> List[Dict]:
    """
    Finds the most semantically relevant chunks for a user query.

    Steps:
    1. Embed the query using the same model as the documents
    2. Search the FAISS index for the nearest vectors
    3. Return the corresponding text chunks

    Args:
        query: User's question or message
        top_k: Number of chunks to retrieve (defaults to settings.rag_top_k)

    Returns:
        List of chunk dicts (sorted by relevance, most relevant first):
        [{"text": "...", "source": "file.pdf", "page": 2, "score": 0.87}, ...]

    Returns empty list if no index exists yet.
    """
    if top_k is None:
        top_k = settings.rag_top_k

    index = _load_faiss_index()
    if index is None or index.ntotal == 0:
        logger.debug("RAG: No index found — returning empty context")
        return []

    metadata = _load_metadata()
    if not metadata:
        logger.debug("RAG: No metadata found — returning empty context")
        return []

    # Embed the query (single text → shape (1, dim))
    query_vector = embed_texts([query])   # Returns shape (1, 1536)

    # Search FAISS — returns distances and indices of top_k nearest vectors
    # D: distances array shape (1, top_k)
    # I: indices array shape (1, top_k)
    actual_k = min(top_k, index.ntotal)
    D, I = index.search(query_vector, actual_k)

    results = []
    for score, idx in zip(D[0], I[0]):
        if idx == -1:   # FAISS returns -1 for empty slots
            continue
        if idx >= len(metadata):
            continue

        chunk = metadata[idx].copy()
        chunk["score"] = float(score)   # Cosine similarity (0 to 1)
        results.append(chunk)

    logger.info(
        f"RAG retrieved {len(results)} chunks for query "
        f"(top score: {results[0]['score']:.3f})" if results else "RAG: no results"
    )
    return results


def format_context_for_prompt(chunks: List[Dict]) -> str:
    """
    Formats retrieved chunks into a clean context block for the GPT prompt.

    The context is injected into the system prompt so GPT can reference
    specific document content when answering.

    Args:
        chunks: List of chunk dicts from retrieve_relevant_chunks()

    Returns:
        Formatted string to insert into the prompt, or "" if no chunks
    """
    if not chunks:
        return ""

    lines = ["=== सन्दर्भ दस्तावेज (Reference Documents) ===\n"]

    for i, chunk in enumerate(chunks, 1):
        source    = chunk.get("source", "अज्ञात")
        page      = chunk.get("page", 0) + 1        # 1-indexed for display
        score     = chunk.get("score", 0)
        text      = chunk.get("text", "").strip()

        lines.append(
            f"[{i}] स्रोत: {source} | पृष्ठ: {page} | "
            f"सान्दर्भिकता: {score:.2f}\n{text}\n"
        )

    lines.append("=== सन्दर्भ समाप्त (End of Context) ===")
    return "\n".join(lines)


def get_indexed_documents() -> List[Dict]:
    """Returns the list of all indexed documents (for the UI)."""
    return _load_documents_list()


def delete_document_from_index(filename: str) -> bool:
    """
    Removes a document from the documents list.

    NOTE: FAISS IndexFlatIP does not support selective vector deletion.
    A full re-index of remaining documents would be needed to truly remove
    vectors. For the thesis scope, we mark it as removed in the documents
    list and rebuild the index from the remaining PDFs on the next startup.

    Phase 5 can add a proper re-indexing job.

    Returns:
        True if the document was found and removed from the list
    """
    docs = _load_documents_list()
    new_docs = [d for d in docs if d["filename"] != filename]

    if len(new_docs) == len(docs):
        return False   # Not found

    _save_documents_list(new_docs)
    logger.info(f"Document removed from index list: {filename}")
    return True


def has_indexed_documents() -> bool:
    """Returns True if at least one document has been indexed."""
    docs = _load_documents_list()
    return len(docs) > 0