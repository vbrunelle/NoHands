from django.urls import path
from . import views

urlpatterns = [
    path('', views.build_list, name='build_list'),
    path('<int:build_id>/', views.build_detail, name='build_detail'),
    path('create/<int:repo_id>/<int:commit_id>/', views.build_create, name='build_create'),
    path('<int:build_id>/start-container/', views.start_build_container, name='start_build_container'),
    path('<int:build_id>/stop-container/', views.stop_build_container, name='stop_build_container'),
    path('<int:build_id>/container-logs/', views.container_logs, name='container_logs'),
]
