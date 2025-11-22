from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'repositories', views.GitRepositoryViewSet)
router.register(r'branches', views.BranchViewSet)
router.register(r'commits', views.CommitViewSet)
router.register(r'builds', views.BuildViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
