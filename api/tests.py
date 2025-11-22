from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from django.utils import timezone
from unittest.mock import patch

from projects.models import GitRepository, Branch, Commit
from builds.models import Build
from .serializers import (
    GitRepositorySerializer, BranchSerializer, CommitSerializer,
    BuildSerializer, BuildCreateSerializer
)


class GitRepositorySerializerTest(TestCase):
    """Tests for GitRepository serializer."""
    
    def test_serializer_with_valid_data(self):
        """Test serializer with valid data."""
        data = {
            'name': 'test-repo',
            'url': 'https://github.com/test/repo.git',
            'description': 'Test repository',
            'default_branch': 'main',
            'is_active': True
        }
        serializer = GitRepositorySerializer(data=data)
        self.assertTrue(serializer.is_valid())
    
    def test_serializer_read(self):
        """Test serializer read."""
        repo = GitRepository.objects.create(
            name='test-repo',
            url='https://github.com/test/repo.git'
        )
        serializer = GitRepositorySerializer(repo)
        self.assertEqual(serializer.data['name'], 'test-repo')
        self.assertEqual(serializer.data['url'], 'https://github.com/test/repo.git')


class BranchSerializerTest(TestCase):
    """Tests for Branch serializer."""
    
    def test_serializer_read(self):
        """Test serializer read."""
        repo = GitRepository.objects.create(
            name='test-repo',
            url='https://github.com/test/repo.git'
        )
        branch = Branch.objects.create(
            repository=repo,
            name='main',
            commit_sha='abc123'
        )
        serializer = BranchSerializer(branch)
        self.assertEqual(serializer.data['name'], 'main')
        self.assertEqual(serializer.data['repository_name'], 'test-repo')


class CommitSerializerTest(TestCase):
    """Tests for Commit serializer."""
    
    def test_serializer_read(self):
        """Test serializer read."""
        repo = GitRepository.objects.create(
            name='test-repo',
            url='https://github.com/test/repo.git'
        )
        commit = Commit.objects.create(
            repository=repo,
            sha='abc123',
            message='Test commit',
            author='Test Author',
            author_email='test@example.com',
            committed_at=timezone.now()
        )
        serializer = CommitSerializer(commit)
        self.assertEqual(serializer.data['sha'], 'abc123')
        self.assertEqual(serializer.data['repository_name'], 'test-repo')


class BuildSerializerTest(TestCase):
    """Tests for Build serializer."""
    
    def test_serializer_read(self):
        """Test serializer read."""
        repo = GitRepository.objects.create(
            name='test-repo',
            url='https://github.com/test/repo.git'
        )
        commit = Commit.objects.create(
            repository=repo,
            sha='abc123',
            message='Test',
            author='Test',
            author_email='test@example.com',
            committed_at=timezone.now()
        )
        build = Build.objects.create(
            repository=repo,
            commit=commit,
            branch_name='main',
            status='success'
        )
        serializer = BuildSerializer(build)
        self.assertEqual(serializer.data['repository_name'], 'test-repo')
        self.assertEqual(serializer.data['commit_sha'], 'abc123')
        self.assertEqual(serializer.data['status'], 'success')


class GitRepositoryViewSetTest(APITestCase):
    """Tests for GitRepository API viewset."""
    
    def setUp(self):
        self.client = APIClient()
        self.repo = GitRepository.objects.create(
            name='test-repo',
            url='https://github.com/test/repo.git',
            is_active=True
        )
    
    def test_list_repositories(self):
        """Test listing repositories."""
        url = reverse('gitrepository-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
    
    def test_retrieve_repository(self):
        """Test retrieving a single repository."""
        url = reverse('gitrepository-detail', args=[self.repo.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'test-repo')


class BranchViewSetTest(APITestCase):
    """Tests for Branch API viewset."""
    
    def setUp(self):
        self.client = APIClient()
        self.repo = GitRepository.objects.create(
            name='test-repo',
            url='https://github.com/test/repo.git'
        )
        self.branch = Branch.objects.create(
            repository=self.repo,
            name='main',
            commit_sha='abc123'
        )
    
    def test_list_branches(self):
        """Test listing branches."""
        url = reverse('branch-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
    
    def test_filter_branches_by_repository(self):
        """Test filtering branches by repository."""
        url = reverse('branch-list')
        response = self.client.get(url, {'repository': self.repo.id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)


class CommitViewSetTest(APITestCase):
    """Tests for Commit API viewset."""
    
    def setUp(self):
        self.client = APIClient()
        self.repo = GitRepository.objects.create(
            name='test-repo',
            url='https://github.com/test/repo.git'
        )
        self.branch = Branch.objects.create(
            repository=self.repo,
            name='main',
            commit_sha='abc123'
        )
        self.commit = Commit.objects.create(
            repository=self.repo,
            branch=self.branch,
            sha='abc123',
            message='Test commit',
            author='Test Author',
            author_email='test@example.com',
            committed_at=timezone.now()
        )
    
    def test_list_commits(self):
        """Test listing commits."""
        url = reverse('commit-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
    
    def test_filter_commits_by_repository(self):
        """Test filtering commits by repository."""
        url = reverse('commit-list')
        response = self.client.get(url, {'repository': self.repo.id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
    
    def test_filter_commits_by_branch(self):
        """Test filtering commits by branch."""
        url = reverse('commit-list')
        response = self.client.get(url, {'branch': self.branch.id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)


class BuildViewSetTest(APITestCase):
    """Tests for Build API viewset."""
    
    def setUp(self):
        self.client = APIClient()
        self.repo = GitRepository.objects.create(
            name='test-repo',
            url='https://github.com/test/repo.git'
        )
        self.commit = Commit.objects.create(
            repository=self.repo,
            sha='abc123',
            message='Test',
            author='Test',
            author_email='test@example.com',
            committed_at=timezone.now()
        )
        self.build = Build.objects.create(
            repository=self.repo,
            commit=self.commit,
            branch_name='main',
            status='success'
        )
    
    def test_list_builds(self):
        """Test listing builds."""
        url = reverse('build-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
    
    def test_retrieve_build(self):
        """Test retrieving a single build."""
        url = reverse('build-detail', args=[self.build.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'success')
    
    def test_filter_builds_by_status(self):
        """Test filtering builds by status."""
        url = reverse('build-list')
        response = self.client.get(url, {'status': 'success'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
    
    @patch('api.views.threading.Thread')
    def test_trigger_build(self, mock_thread):
        """Test triggering a build via API."""
        url = reverse('build-trigger')
        data = {
            'repository_id': self.repo.id,
            'commit_id': self.commit.id,
            'push_to_registry': False,
            'deploy_after_build': False
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('id', response.data)
        
        # Verify build was created
        new_build = Build.objects.get(id=response.data['id'])
        self.assertEqual(new_build.repository, self.repo)
        self.assertEqual(new_build.commit, self.commit)
        
        # Verify thread was started
        mock_thread.assert_called_once()
    
    def test_trigger_build_invalid_repository(self):
        """Test triggering build with invalid repository."""
        url = reverse('build-trigger')
        data = {
            'repository_id': 9999,
            'commit_id': self.commit.id,
            'push_to_registry': False,
            'deploy_after_build': False
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class APIURLRoutingTest(TestCase):
    """Tests for API URL routing."""
    
    def test_repositories_url_resolves(self):
        """Test repositories API URL resolves correctly."""
        url = reverse('gitrepository-list')
        self.assertEqual(url, '/api/repositories/')
    
    def test_branches_url_resolves(self):
        """Test branches API URL resolves correctly."""
        url = reverse('branch-list')
        self.assertEqual(url, '/api/branches/')
    
    def test_commits_url_resolves(self):
        """Test commits API URL resolves correctly."""
        url = reverse('commit-list')
        self.assertEqual(url, '/api/commits/')
    
    def test_builds_url_resolves(self):
        """Test builds API URL resolves correctly."""
        url = reverse('build-list')
        self.assertEqual(url, '/api/builds/')
    
    def test_build_trigger_url_resolves(self):
        """Test build trigger API URL resolves correctly."""
        url = reverse('build-trigger')
        self.assertEqual(url, '/api/builds/trigger/')
