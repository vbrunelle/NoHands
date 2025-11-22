from django.urls import path
from . import views

urlpatterns = [
    path('', views.repository_list, name='repository_list'),
    path('initial-setup/', views.initial_setup, name='initial_setup'),
    path('connect/', views.connect_github_repository, name='connect_github_repository'),
    path('<int:repo_id>/', views.repository_detail, name='repository_detail'),
    path('<int:repo_id>/branch/<int:branch_id>/', views.branch_commits, name='branch_commits'),
]
