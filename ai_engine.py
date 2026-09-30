"""
AI engine: RAG-based summarization and Q&A using Ollama (local, free).
Ollama runs Mistral/Llama3 locally — no API key required.
"""
import logging
import requests
from django.conf import settings
from .vector_store import retrieve_relevant_chunks

logger = logging.getLogger(__name__)

SUMMARY_SECTIONS = {
    'overview': (
        "You are a legal document expert. Based ONLY on the provided legal document excerpts, "
        "write a brief 2-3 sentence plain-English overview of what this document is about. "
        "Do not use legal jargon. Respond in plain text only."
    ),
    'rights': (
        "You are a legal document expert. Based ONLY on the provided excerpts, "
        "list all RIGHTS granted to the person signing this document. "
        "Use simple bullet points starting with '•'. Each right should be 1-2 plain sentences. "
        "If no clear rights are mentioned, say 'No explicit rights found in the reviewed sections.'"
    ),
    'obligations': (
        "You are a legal document expert. Based ONLY on the provided excerpts, "
        "list all OBLIGATIONS and DUTIES the signing party must fulfil. "
        "Use simple bullet points starting with '•'. Be specific about deadlines, payments, or actions required. "
        "If none found, say 'No explicit obligations found in the reviewed sections.'"
    ),
    'risks': (
        "You are a legal document expert. Based ONLY on the provided excerpts, "
        "identify all RISKS the signing party is taking on — financial, legal, or personal. "
        "Use simple bullet points starting with '•'. Explain each risk in plain English. "
        "If none found, say 'No significant risks identified in the reviewed sections.'"
    ),
    'red_flags': (
        "You are a legal document expert. Based ONLY on the provided excerpts, "
        "identify any RED FLAGS or UNFAIR CLAUSES — hidden fees, unusual termination clauses, "
        "waived rights, auto-renewals, liability limitations, or one-sided terms. "
        "Use bullet points starting with '🚩'. Be direct and warn the user clearly. "
        "If none found, say 'No red flags identified in the reviewed sections.'"
    ),
}

SECTION_QUERIES = {
    'overview': 'What is this document about? What is the purpose?',
    'rights': 'rights entitlements permissions granted to the party',
    'obligations': 'obligations duties responsibilities payments required',
    'risks': 'risks consequences penalties liability damages',
    'red_flags': 'unfair clauses auto-renewal hidden fees waived rights termination penalty',
}


def call_ollama(prompt: str, system: str = "") -> str:
    """
    Call local Ollama API. Returns plain text response.
    Falls back to a helpful message if Ollama is not running.
    """
    url = f"{settings.OLLAMA_BASE_URL}/api/generate"
    payload = {
        "model": settings.OLLAMA_MODEL,
        "prompt": prompt,
        "system": system,
        "stream": False,
        "options": {
            "temperature": 0.2,
            "num_predict": 800,
        }
    }

    try:
        response = requests.post(url, json=payload, timeout=120)
        response.raise_for_status()
        return response.json().get('response', '').strip()
    except requests.exceptions.ConnectionError:
        logger.error("Ollama not running. Start with: ollama serve")
        return "[Ollama is not running. Start Ollama with 'ollama serve' and ensure 'mistral' is pulled.]"
    except Exception as e:
        logger.error(f"Ollama call failed: {e}")
        return f"[AI processing failed: {e}]"


def summarize_document(document_id: int, raw_text: str) -> dict:
    """
    Generate a 5-section summary (overview, rights, obligations, risks, red_flags)
    using RAG: retrieve relevant chunks per section, then prompt Ollama.
    """
    summary = {}

    for section, system_prompt in SUMMARY_SECTIONS.items():
        query = SECTION_QUERIES[section]
        chunks = retrieve_relevant_chunks(document_id, query, top_k=6)

        if not chunks:
            # Fall back to first 3000 chars of raw text
            context = raw_text[:3000]
        else:
            context = "\n\n---\n\n".join(chunks)

        prompt = (
            f"Here are relevant excerpts from the legal document:\n\n"
            f"{context}\n\n"
            f"---\n\n"
            f"Task: {system_prompt}"
        )

        logger.info(f"Generating '{section}' section for document {document_id}")
        summary[section] = call_ollama(prompt, system=system_prompt)

    return summary


def answer_question(document_id: int, question: str) -> str:
    """
    Answer a specific question about a document using RAG.
    Only uses context retrieved from the document — no hallucination.
    """
    chunks = retrieve_relevant_chunks(document_id, question, top_k=5)

    if not chunks:
        return "I could not find relevant information in this document to answer your question."

    context = "\n\n---\n\n".join(chunks)
    system = (
        "You are a legal document assistant. Answer ONLY based on the provided document excerpts. "
        "If the answer is not in the excerpts, say so clearly. "
        "Use plain English. Be concise and direct."
    )
    prompt = (
        f"Document excerpts:\n\n{context}\n\n"
        f"---\n\n"
        f"Question: {question}\n\n"
        f"Answer:"
    )

    return call_ollama(prompt, system=system)