"""
Celery tasks for background document processing.
All heavy work (PDF extraction, embedding, AI summarization) runs async.
"""
import logging
import os
from celery import shared_task
from django.core.files.base import ContentFile

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def process_document(self, document_id: int):
    """
    Full pipeline:
    1. Extract text from PDF
    2. Chunk text
    3. Embed chunks into ChromaDB
    4. Generate AI summary
    5. Generate simplified PDF
    """
    from .models import Document, Summary
    from .services.pdf_extractor import extract_text_from_pdf, chunk_text
    from .services.vector_store import embed_and_store
    from .services.ai_engine import summarize_document
    from .services.pdf_generator import generate_simplified_pdf

    try:
        doc = Document.objects.get(id=document_id)
    except Document.DoesNotExist:
        logger.error(f"Document {document_id} not found")
        return

    try:
        # Step 1: Extract text
        doc.status = 'extracting'
        doc.save(update_fields=['status'])

        file_path = doc.original_file.path
        raw_text, page_count = extract_text_from_pdf(file_path)
        doc.raw_text = raw_text
        doc.page_count = page_count
        doc.save(update_fields=['raw_text', 'page_count'])

        # Step 2: Chunk text
        chunks = chunk_text(raw_text)

        # Step 3: Embed and store in ChromaDB
        doc.status = 'processing'
        doc.save(update_fields=['status'])
        embed_and_store(document_id, chunks)

        # Step 4: AI summarization
        summary_data = summarize_document(document_id, raw_text)

        summary, _ = Summary.objects.get_or_create(document=doc)
        summary.overview = summary_data.get('overview', '')
        summary.rights = summary_data.get('rights', '')
        summary.obligations = summary_data.get('obligations', '')
        summary.risks = summary_data.get('risks', '')
        summary.red_flags = summary_data.get('red_flags', '')
        summary.save()

        # Step 5: Generate simplified PDF
        pdf_bytes = generate_simplified_pdf(doc.title, summary_data)
        pdf_filename = f"simplified_{document_id}.pdf"
        doc.simplified_pdf.save(pdf_filename, ContentFile(pdf_bytes), save=False)

        doc.status = 'ready'
        doc.save(update_fields=['status', 'simplified_pdf'])

        logger.info(f"Document {document_id} processed successfully")
        return {'status': 'success', 'document_id': document_id}

    except Exception as exc:
        logger.error(f"Document {document_id} processing failed: {exc}")
        try:
            doc.status = 'failed'
            doc.save(update_fields=['status'])
        except Exception:
            pass
        raise self.retry(exc=exc, countdown=60)


@shared_task
def answer_question_task(question_id: int):
    """Answer a user question asynchronously."""
    from .models import Question
    from .services.ai_engine import answer_question

    try:
        q = Question.objects.get(id=question_id)
        answer = answer_question(q.document_id, q.question_text)
        q.answer_text = answer
        q.save(update_fields=['answer_text'])
        logger.info(f"Answered question {question_id}")
    except Exception as e:
        logger.error(f"Failed to answer question {question_id}: {e}")