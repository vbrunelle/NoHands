from django.urls import path
from . import views

urlpatterns = [
    path('', views.build_list, name='build_list'),
    path('<int:build_id>/', views.build_detail, name='build_detail'),
    path('create/<int:repo_id>/<int:commit_id>/', views.build_create, name='build_create'),
]
