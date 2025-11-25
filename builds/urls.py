from django.urls import path
from . import views

urlpatterns = [
    path('', views.build_list, name='build_list'),
    path('<int:build_id>/', views.build_detail, name='build_detail'),
    path('create/<int:repo_id>/<int:commit_id>/', views.build_create, name='build_create'),
    path('<int:build_id>/start-container/', views.start_build_container, name='start_build_container'),
    path('<int:build_id>/stop-container/', views.stop_build_container, name='stop_build_container'),
    path('<int:build_id>/container-logs/', views.container_logs, name='container_logs'),
    # API endpoints for file selection
    path('api/files/<int:repo_id>/<int:commit_id>/', views.list_commit_files, name='list_commit_files'),
    path('api/file-content/<int:repo_id>/<int:commit_id>/', views.get_commit_file_content, name='get_commit_file_content'),
    # API endpoint for Dockerfile templates
    path('api/templates/<str:template_name>/', views.get_dockerfile_template, name='get_dockerfile_template'),
]
