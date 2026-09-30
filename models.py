from django.db import models
from django.conf import settings


class Document(models.Model):
    STATUS_CHOICES = [
        ('uploaded', 'Uploaded'),
        ('extracting', 'Extracting Text'),
        ('processing', 'Processing AI'),
        ('ready', 'Ready'),
        ('failed', 'Failed'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='documents')
    title = models.CharField(max_length=255)
    original_file = models.FileField(upload_to='documents/originals/')
    simplified_pdf = models.FileField(upload_to='documents/simplified/', blank=True, null=True)
    raw_text = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='uploaded')
    page_count = models.PositiveIntegerField(default=0)
    file_size = models.PositiveIntegerField(default=0)  # bytes
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} ({self.user.email})"


class Summary(models.Model):
    document = models.OneToOneField(Document, on_delete=models.CASCADE, related_name='summary')
    rights = models.TextField(blank=True)
    obligations = models.TextField(blank=True)
    risks = models.TextField(blank=True)
    red_flags = models.TextField(blank=True)
    overview = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Summary for {self.document.title}"


class Question(models.Model):
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='questions')
    question_text = models.TextField()
    answer_text = models.TextField(blank=True)
    is_anonymous = models.BooleanField(default=True)
    asked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='questions'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Q: {self.question_text[:60]}"