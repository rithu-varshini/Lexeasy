from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, logout, authenticate
from django.contrib import messages
from .models import Document


def home(request):
    return render(request, 'documents/home.html')


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        user = authenticate(request, username=email, password=password)
        if user:
            login(request, user)
            return redirect('dashboard')
        messages.error(request, 'Invalid email or password.')
    return render(request, 'users/login.html')


def register_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        from django.contrib.auth import get_user_model
        User = get_user_model()
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        password2 = request.POST.get('password2')

        if password != password2:
            messages.error(request, 'Passwords do not match.')
        elif User.objects.filter(email=email).exists():
            messages.error(request, 'Email already registered.')
        else:
            user = User.objects.create_user(username=username, email=email, password=password)
            login(request, user)
            return redirect('dashboard')
    return render(request, 'users/register.html')


def logout_view(request):
    logout(request)
    return redirect('home')


@login_required
def dashboard(request):
    documents = Document.objects.filter(user=request.user)
    return render(request, 'documents/dashboard.html', {'documents': documents})


@login_required
def upload_view(request):
    if request.method == 'POST':
        from django.core.files.storage import default_storage
        from .tasks import process_document
        title = request.POST.get('title', '').strip()
        pdf_file = request.FILES.get('pdf_file')

        if not title or not pdf_file:
            messages.error(request, 'Please provide both a title and a PDF file.')
            return render(request, 'documents/upload.html')

        if not pdf_file.name.lower().endswith('.pdf'):
            messages.error(request, 'Only PDF files are accepted.')
            return render(request, 'documents/upload.html')

        if pdf_file.size > 20 * 1024 * 1024:
            messages.error(request, 'File size must not exceed 20 MB.')
            return render(request, 'documents/upload.html')

        doc = Document.objects.create(
            user=request.user,
            title=title,
            original_file=pdf_file,
            file_size=pdf_file.size,
        )
        process_document.delay(doc.id)
        messages.success(request, 'Document uploaded! Processing has started.')
        return redirect('summary_view', pk=doc.id)

    return render(request, 'documents/upload.html')


@login_required
def summary_view(request, pk):
    doc = get_object_or_404(Document, id=pk, user=request.user)
    summary = getattr(doc, 'summary', None)
    questions = doc.questions.all()[:20]
    return render(request, 'documents/summary.html', {
        'document': doc,
        'summary': summary,
        'questions': questions,
    })


@login_required
def ask_question_view(request, pk):
    doc = get_object_or_404(Document, id=pk, user=request.user)
    if request.method == 'POST':
        from .models import Question
        from .tasks import answer_question_task
        question_text = request.POST.get('question', '').strip()
        is_anonymous = request.POST.get('anonymous') == 'on'
        if question_text:
            q = Question.objects.create(
                document=doc,
                question_text=question_text,
                is_anonymous=is_anonymous,
                asked_by=None if is_anonymous else request.user,
            )
            answer_question_task.delay(q.id)
            messages.success(request, 'Your question has been submitted. The answer will appear shortly.')
        return redirect('summary_view', pk=pk)
    return redirect('summary_view', pk=pk)