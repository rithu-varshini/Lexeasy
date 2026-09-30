from django.urls import path
from .template_views import (
    home, login_view, register_view, logout_view,
    dashboard, upload_view, summary_view, ask_question_view,
)

urlpatterns = [
    path('', home, name='home'),
    path('login/', login_view, name='login'),
    path('register/', register_view, name='register'),
    path('logout/', logout_view, name='logout'),
    path('dashboard/', dashboard, name='dashboard'),
    path('upload/', upload_view, name='upload'),
    path('documents/<int:pk>/', summary_view, name='summary_view'),
    path('documents/<int:pk>/ask/', ask_question_view, name='ask_question'),
]