"""
ChromaDB vector store integration.
Embeds document chunks using sentence-transformers (free, local).
"""
import logging
from django.conf import settings

import chromadb
from chromadb.config import Settings as ChromaSettings
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

# Singleton embedding model — loaded once per process
_embedding_model = None


def get_embedding_model() -> SentenceTransformer:
    global _embedding_model
    if _embedding_model is None:
        logger.info("Loading sentence-transformer model (all-MiniLM-L6-v2)...")
        _embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
    return _embedding_model


def get_chroma_client() -> chromadb.PersistentClient:
    return chromadb.PersistentClient(
        path=settings.CHROMA_PERSIST_DIR,
        settings=ChromaSettings(anonymized_telemetry=False),
    )


def get_collection_name(document_id: int) -> str:
    return f"doc_{document_id}"


def embed_and_store(document_id: int, chunks: list[str]) -> None:
    """
    Embed text chunks and store them in ChromaDB under a per-document collection.
    """
    model = get_embedding_model()
    client = get_chroma_client()
    collection_name = get_collection_name(document_id)

    # Delete existing collection if re-processing
    try:
        client.delete_collection(collection_name)
    except Exception:
        pass

    collection = client.create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine"},
    )

    # Embed in batches to avoid OOM
    batch_size = 50
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i + batch_size]
        embeddings = model.encode(batch, show_progress_bar=False).tolist()
        ids = [f"chunk_{i + j}" for j in range(len(batch))]
        collection.add(
            documents=batch,
            embeddings=embeddings,
            ids=ids,
        )

    logger.info(f"Stored {len(chunks)} chunks for document {document_id}")


def retrieve_relevant_chunks(document_id: int, query: str, top_k: int = 5) -> list[str]:
    """
    Retrieve the most relevant chunks for a given query using cosine similarity.
    """
    model = get_embedding_model()
    client = get_chroma_client()
    collection_name = get_collection_name(document_id)

    try:
        collection = client.get_collection(collection_name)
    except Exception:
        logger.warning(f"Collection not found for document {document_id}")
        return []

    query_embedding = model.encode([query], show_progress_bar=False).tolist()
    results = collection.query(
        query_embeddings=query_embedding,
        n_results=min(top_k, collection.count()),
    )

    return results['documents'][0] if results['documents'] else []


def delete_document_collection(document_id: int) -> None:
    """Clean up ChromaDB collection when document is deleted."""
    client = get_chroma_client()
    try:
        client.delete_collection(get_collection_name(document_id))
    except Exception:
        pass