from rest_framework import serializers
from .models import Document, Summary, Question


class SummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = Summary
        fields = ('overview', 'rights', 'obligations', 'risks', 'red_flags', 'updated_at')


class DocumentListSerializer(serializers.ModelSerializer):
    has_summary = serializers.SerializerMethodField()

    class Meta:
        model = Document
        fields = (
            'id', 'title', 'status', 'page_count',
            'file_size', 'has_summary', 'created_at',
        )

    def get_has_summary(self, obj):
        return hasattr(obj, 'summary') and bool(obj.summary.overview)


class DocumentDetailSerializer(serializers.ModelSerializer):
    summary = SummarySerializer(read_only=True)
    has_simplified_pdf = serializers.SerializerMethodField()

    class Meta:
        model = Document
        fields = (
            'id', 'title', 'status', 'page_count',
            'file_size', 'summary', 'has_simplified_pdf', 'created_at',
        )

    def get_has_simplified_pdf(self, obj):
        return bool(obj.simplified_pdf)


class DocumentUploadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Document
        fields = ('id', 'title', 'original_file', 'status', 'created_at')
        read_only_fields = ('id', 'status', 'created_at')

    def validate_original_file(self, value):
        if not value.name.lower().endswith('.pdf'):
            raise serializers.ValidationError("Only PDF files are accepted.")
        max_size = 20 * 1024 * 1024  # 20 MB
        if value.size > max_size:
            raise serializers.ValidationError("File size must not exceed 20 MB.")
        return value

    def validate_title(self, value):
        if not value.strip():
            raise serializers.ValidationError("Title cannot be empty.")
        return value.strip()

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        validated_data['file_size'] = validated_data['original_file'].size
        return super().create(validated_data)


class QuestionSerializer(serializers.ModelSerializer):
    display_name = serializers.SerializerMethodField()

    class Meta:
        model = Question
        fields = (
            'id', 'question_text', 'answer_text',
            'is_anonymous', 'display_name', 'created_at',
        )
        read_only_fields = ('id', 'answer_text', 'created_at')

    def get_display_name(self, obj):
        if obj.is_anonymous or not obj.asked_by:
            return 'Anonymous'
        return obj.asked_by.username

    def create(self, validated_data):
        request = self.context['request']
        document_id = self.context['document_id']
        validated_data['document_id'] = document_id
        if not validated_data.get('is_anonymous', True):
            validated_data['asked_by'] = request.user
        return super().create(validated_data)