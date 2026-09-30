import logging
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Document, Summary, Question
from .serializers import (
    DocumentListSerializer, DocumentDetailSerializer,
    DocumentUploadSerializer, QuestionSerializer,
)
from .tasks import process_document, answer_question_task

logger = logging.getLogger(__name__)


class DocumentUploadView(generics.CreateAPIView):
    """
    POST /api/documents/upload/
    Upload a PDF, trigger background processing.
    """
    serializer_class = DocumentUploadSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def perform_create(self, serializer):
        doc = serializer.save()
        # Kick off async processing pipeline
        process_document.delay(doc.id)
        logger.info(f"Queued processing for document {doc.id}")

    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        response.data['message'] = (
            'Document uploaded. Processing has started — '
            'refresh in a moment to see your summary.'
        )
        return response


class DocumentListView(generics.ListAPIView):
    """
    GET /api/documents/
    Paginated list of current user's documents.
    """
    serializer_class = DocumentListSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        return Document.objects.filter(user=self.request.user).select_related('summary')


class DocumentDetailView(generics.RetrieveAPIView):
    """
    GET /api/documents/<id>/
    Full document detail including summary.
    """
    serializer_class = DocumentDetailSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        return Document.objects.filter(user=self.request.user).select_related('summary')


class DocumentDeleteView(generics.DestroyAPIView):
    """
    DELETE /api/documents/<id>/
    """
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        return Document.objects.filter(user=self.request.user)

    def perform_destroy(self, instance):
        from .services.vector_store import delete_document_collection
        delete_document_collection(instance.id)
        instance.delete()


class RetriggerSummarizeView(APIView):
    """
    POST /api/documents/<id>/summarize/
    Re-trigger processing if failed or to refresh.
    """
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request, pk):
        doc = get_object_or_404(Document, id=pk, user=request.user)
        doc.status = 'uploaded'
        doc.save(update_fields=['status'])
        process_document.delay(doc.id)
        return Response({'message': 'Processing retriggered.'})


class DocumentStatusView(APIView):
    """
    GET /api/documents/<id>/status/
    Poll processing status.
    """
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request, pk):
        doc = get_object_or_404(Document, id=pk, user=request.user)
        return Response({
            'id': doc.id,
            'status': doc.status,
            'title': doc.title,
        })


class DownloadSimplifiedPDFView(APIView):
    """
    GET /api/documents/<id>/download/
    Stream the simplified PDF to the browser.
    """
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request, pk):
        doc = get_object_or_404(Document, id=pk, user=request.user)
        if not doc.simplified_pdf:
            return Response(
                {'error': 'Simplified PDF not yet generated. Check back once processing is complete.'},
                status=status.HTTP_404_NOT_FOUND
            )
        response = FileResponse(
            doc.simplified_pdf.open('rb'),
            content_type='application/pdf',
        )
        safe_title = "".join(c for c in doc.title if c.isalnum() or c in " _-")[:50]
        response['Content-Disposition'] = f'attachment; filename="LexEasy_{safe_title}.pdf"'
        return response


class QuestionListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/documents/<id>/questions/  — public Q&A thread
    POST /api/documents/<id>/questions/  — ask a question
    """
    serializer_class = QuestionSerializer
    permission_classes = (permissions.IsAuthenticatedOrReadOnly,)

    def get_queryset(self):
        return Question.objects.filter(
            document_id=self.kwargs['pk']
        ).select_related('asked_by')

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx['document_id'] = self.kwargs['pk']
        return ctx

    def perform_create(self, serializer):
        question = serializer.save()
        # Answer asynchronously
        answer_question_task.delay(question.id)