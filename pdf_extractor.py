"""
PDF text extraction using PyPDF2.
Splits text into LangChain-compatible chunks for embedding.
"""
import logging
from pathlib import Path

import PyPDF2
from langchain.text_splitter import RecursiveCharacterTextSplitter

logger = logging.getLogger(__name__)


def extract_text_from_pdf(file_path: str) -> tuple[str, int]:
    """
    Extract raw text and page count from a PDF file.
    Returns (raw_text, page_count).
    """
    raw_text = ""
    page_count = 0

    try:
        with open(file_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            page_count = len(reader.pages)

            for page_num, page in enumerate(reader.pages):
                try:
                    text = page.extract_text()
                    if text:
                        raw_text += f"\n\n--- Page {page_num + 1} ---\n\n{text}"
                except Exception as e:
                    logger.warning(f"Could not extract page {page_num + 1}: {e}")

    except Exception as e:
        logger.error(f"Failed to read PDF at {file_path}: {e}")
        raise ValueError(f"Could not read PDF: {e}")

    if not raw_text.strip():
        raise ValueError("No text could be extracted from this PDF. It may be scanned/image-based.")

    return raw_text.strip(), page_count


def chunk_text(raw_text: str) -> list[str]:
    """
    Split raw text into overlapping chunks suitable for embedding.
    Chunk size 1000 chars with 200 char overlap balances context and retrieval quality.
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        separators=["\n\n", "\n", ".", " ", ""],
    )
    chunks = splitter.split_text(raw_text)
    logger.info(f"Text split into {len(chunks)} chunks")
    return chunks