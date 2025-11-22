from django.urls import path
from . import views

urlpatterns = [
    path('', views.repository_list, name='repository_list'),
    path('<int:repo_id>/', views.repository_detail, name='repository_detail'),
    path('<int:repo_id>/branch/<int:branch_id>/', views.branch_commits, name='branch_commits'),
]
