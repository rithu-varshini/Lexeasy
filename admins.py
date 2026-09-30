from django.contrib import admin
from .models import Document, Summary, Question

@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'status', 'page_count', 'created_at')
    list_filter = ('status',)
    search_fields = ('title', 'user__email')

@admin.register(Summary)
class SummaryAdmin(admin.ModelAdmin):
    list_display = ('document', 'created_at')

@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('question_text', 'document', 'is_anonymous', 'created_at')