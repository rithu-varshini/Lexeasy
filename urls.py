from django.urls import path
from .views import (
    DocumentUploadView, DocumentListView, DocumentDetailView,
    DocumentDeleteView, RetriggerSummarizeView, DocumentStatusView,
    DownloadSimplifiedPDFView, QuestionListCreateView,
)

urlpatterns = [
    path('documents/upload/', DocumentUploadView.as_view(), name='document-upload'),
    path('documents/', DocumentListView.as_view(), name='document-list'),
    path('documents/<int:pk>/', DocumentDetailView.as_view(), name='document-detail'),
    path('documents/<int:pk>/delete/', DocumentDeleteView.as_view(), name='document-delete'),
    path('documents/<int:pk>/summarize/', RetriggerSummarizeView.as_view(), name='document-summarize'),
    path('documents/<int:pk>/status/', DocumentStatusView.as_view(), name='document-status'),
    path('documents/<int:pk>/download/', DownloadSimplifiedPDFView.as_view(), name='document-download'),
    path('documents/<int:pk>/questions/', QuestionListCreateView.as_view(), name='document-questions'),
]