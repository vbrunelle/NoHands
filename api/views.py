from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
import threading

from projects.models import GitRepository, Branch, Commit
from builds.models import Build
from builds.views import execute_build
from .serializers import (
    GitRepositorySerializer, BranchSerializer, CommitSerializer,
    BuildSerializer, BuildCreateSerializer
)


class GitRepositoryViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoint for Git repositories."""
    queryset = GitRepository.objects.filter(is_active=True)
    serializer_class = GitRepositorySerializer


class BranchViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoint for branches."""
    queryset = Branch.objects.all()
    serializer_class = BranchSerializer
    
    def get_queryset(self):
        queryset = Branch.objects.all()
        repo_id = self.request.query_params.get('repository')
        if repo_id:
            queryset = queryset.filter(repository_id=repo_id)
        return queryset


class CommitViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoint for commits."""
    queryset = Commit.objects.all()
    serializer_class = CommitSerializer
    
    def get_queryset(self):
        queryset = Commit.objects.all()
        repo_id = self.request.query_params.get('repository')
        branch_id = self.request.query_params.get('branch')
        if repo_id:
            queryset = queryset.filter(repository_id=repo_id)
        if branch_id:
            queryset = queryset.filter(branch_id=branch_id)
        return queryset


class BuildViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoint for builds."""
    queryset = Build.objects.all()
    serializer_class = BuildSerializer
    
    def get_queryset(self):
        queryset = Build.objects.all()
        repo_id = self.request.query_params.get('repository')
        status_filter = self.request.query_params.get('status')
        if repo_id:
            queryset = queryset.filter(repository_id=repo_id)
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        return queryset
    
    @action(detail=False, methods=['post'])
    def trigger(self, request):
        """Trigger a new build."""
        serializer = BuildCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            repository = GitRepository.objects.get(id=serializer.validated_data['repository_id'])
            commit = Commit.objects.get(
                id=serializer.validated_data['commit_id'],
                repository=repository
            )
            
            # Create build
            build = Build.objects.create(
                repository=repository,
                commit=commit,
                branch_name=commit.branch.name if commit.branch else 'unknown',
                status='pending',
                push_to_registry=serializer.validated_data['push_to_registry'],
                deploy_after_build=serializer.validated_data['deploy_after_build']
            )
            
            # Start build in background
            thread = threading.Thread(target=execute_build, args=(build.id,))
            thread.daemon = True
            thread.start()
            
            return Response(
                BuildSerializer(build).data,
                status=status.HTTP_201_CREATED
            )
        except GitRepository.DoesNotExist:
            return Response(
                {'error': 'Repository not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Commit.DoesNotExist:
            return Response(
                {'error': 'Commit not found'},
                status=status.HTTP_404_NOT_FOUND
            )

