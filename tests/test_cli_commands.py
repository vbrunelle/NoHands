"""
Tests for CLI management commands.
"""
import json
from io import StringIO
from django.test import TestCase
from django.core.management import call_command
from django.core.management.base import CommandError
from django.contrib.auth.models import User
from django.utils import timezone
from unittest.mock import patch, MagicMock

from projects.models import GitRepository, Branch, Commit
from builds.models import Build


class RepoListCommandTest(TestCase):
    """Tests for repo_list command."""
    
    def setUp(self):
        self.repo1 = GitRepository.objects.create(
            name='alpha-repo',
            url='https://github.com/test/alpha.git',
            is_active=True,
            default_branch='main'
        )
        self.repo2 = GitRepository.objects.create(
            name='beta-repo',
            url='https://github.com/test/beta.git',
            is_active=False,
            default_branch='master'
        )
    
    def test_list_all_repositories(self):
        """Test listing all repositories."""
        out = StringIO()
        call_command('repo_list', stdout=out)
        output = out.getvalue()
        
        self.assertIn('alpha-repo', output)
        self.assertIn('beta-repo', output)
        self.assertIn('Found 2', output)
    
    def test_list_active_only(self):
        """Test listing only active repositories."""
        out = StringIO()
        call_command('repo_list', '--active-only', stdout=out)
        output = out.getvalue()
        
        self.assertIn('alpha-repo', output)
        self.assertNotIn('beta-repo', output)
        self.assertIn('Found 1', output)
    
    def test_list_json_format(self):
        """Test listing repositories in JSON format."""
        out = StringIO()
        call_command('repo_list', '--format=json', stdout=out)
        output = out.getvalue()
        
        data = json.loads(output)
        self.assertEqual(len(data), 2)
        self.assertEqual(data[0]['name'], 'alpha-repo')
    
    def test_list_empty(self):
        """Test listing when no repositories exist."""
        GitRepository.objects.all().delete()
        out = StringIO()
        call_command('repo_list', stdout=out)
        output = out.getvalue()
        
        self.assertIn('No repositories found', output)


class RepoConnectCommandTest(TestCase):
    """Tests for repo_connect command."""
    
    def test_connect_repository(self):
        """Test connecting a new repository."""
        out = StringIO()
        call_command(
            'repo_connect',
            'test-repo',
            'https://github.com/test/repo.git',
            '--default-branch=main',
            stdout=out
        )
        output = out.getvalue()
        
        self.assertIn('created successfully', output)
        self.assertTrue(GitRepository.objects.filter(name='test-repo').exists())
    
    def test_connect_repository_with_options(self):
        """Test connecting repository with all options."""
        out = StringIO()
        call_command(
            'repo_connect',
            'full-repo',
            'https://github.com/test/full.git',
            '--description=Full test repo',
            '--default-branch=develop',
            '--dockerfile-path=docker/Dockerfile',
            stdout=out
        )
        
        repo = GitRepository.objects.get(name='full-repo')
        self.assertEqual(repo.description, 'Full test repo')
        self.assertEqual(repo.default_branch, 'develop')
        self.assertEqual(repo.dockerfile_path, 'docker/Dockerfile')
    
    def test_connect_duplicate_repository(self):
        """Test that connecting duplicate repository raises error."""
        GitRepository.objects.create(
            name='existing-repo',
            url='https://github.com/test/existing.git'
        )
        
        out = StringIO()
        with self.assertRaises(CommandError) as context:
            call_command(
                'repo_connect',
                'existing-repo',
                'https://github.com/test/new.git',
                stdout=out
            )
        
        self.assertIn('already exists', str(context.exception))
    
    def test_connect_with_user(self):
        """Test connecting repository with user association."""
        user = User.objects.create_user(username='testuser', password='testpass')
        out = StringIO()
        call_command(
            'repo_connect',
            'user-repo',
            'https://github.com/test/user.git',
            '--user=testuser',
            stdout=out
        )
        
        repo = GitRepository.objects.get(name='user-repo')
        self.assertEqual(repo.user, user)
    
    def test_connect_with_invalid_user(self):
        """Test that connecting with invalid user raises error."""
        out = StringIO()
        with self.assertRaises(CommandError) as context:
            call_command(
                'repo_connect',
                'user-repo',
                'https://github.com/test/user.git',
                '--user=nonexistent',
                stdout=out
            )
        
        self.assertIn('not found', str(context.exception))


class RepoRefreshCommandTest(TestCase):
    """Tests for repo_refresh command."""
    
    def setUp(self):
        self.repo = GitRepository.objects.create(
            name='test-repo',
            url='https://github.com/test/repo.git'
        )
    
    @patch('projects.management.commands.repo_refresh.clone_or_update_repo')
    @patch('projects.management.commands.repo_refresh.list_branches')
    def test_refresh_branches(self, mock_list_branches, mock_clone):
        """Test refreshing branches."""
        mock_list_branches.return_value = [
            {'name': 'main', 'commit_sha': 'abc123'},
            {'name': 'develop', 'commit_sha': 'def456'},
        ]
        
        out = StringIO()
        call_command('repo_refresh', str(self.repo.id), stdout=out)
        output = out.getvalue()
        
        self.assertIn('Refreshed 2 branch', output)
        self.assertTrue(Branch.objects.filter(repository=self.repo, name='main').exists())
        self.assertTrue(Branch.objects.filter(repository=self.repo, name='develop').exists())
    
    @patch('projects.management.commands.repo_refresh.clone_or_update_repo')
    @patch('projects.management.commands.repo_refresh.list_branches')
    def test_refresh_by_name(self, mock_list_branches, mock_clone):
        """Test refreshing branches by repository name."""
        mock_list_branches.return_value = [{'name': 'main', 'commit_sha': 'abc123'}]
        
        out = StringIO()
        call_command('repo_refresh', 'test-repo', stdout=out)
        output = out.getvalue()
        
        self.assertIn('Refreshed 1 branch', output)
    
    def test_refresh_nonexistent_repo(self):
        """Test refreshing non-existent repository."""
        out = StringIO()
        with self.assertRaises(CommandError) as context:
            call_command('repo_refresh', '9999', stdout=out)
        
        self.assertIn('not found', str(context.exception))


class BranchCommitsCommandTest(TestCase):
    """Tests for branch_commits command."""
    
    def setUp(self):
        self.repo = GitRepository.objects.create(
            name='test-repo',
            url='https://github.com/test/repo.git',
            default_branch='main'
        )
        self.branch = Branch.objects.create(
            repository=self.repo,
            name='main',
            commit_sha='abc123'
        )
        self.commit = Commit.objects.create(
            repository=self.repo,
            branch=self.branch,
            sha='abc123def456',
            message='Test commit',
            author='Test Author',
            author_email='test@example.com',
            committed_at=timezone.now()
        )
    
    def test_list_commits(self):
        """Test listing commits."""
        out = StringIO()
        call_command('branch_commits', str(self.repo.id), stdout=out)
        output = out.getvalue()
        
        self.assertIn('abc123de', output)
        self.assertIn('Test commit', output)
    
    def test_list_commits_json(self):
        """Test listing commits in JSON format."""
        out = StringIO()
        call_command('branch_commits', str(self.repo.id), '--format=json', stdout=out)
        output = out.getvalue()
        
        data = json.loads(output)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['author'], 'Test Author')
    
    def test_list_commits_nonexistent_branch(self):
        """Test listing commits for non-existent branch."""
        out = StringIO()
        with self.assertRaises(CommandError) as context:
            call_command('branch_commits', str(self.repo.id), '--branch=nonexistent', stdout=out)
        
        self.assertIn('not found', str(context.exception))


class BuildListCommandTest(TestCase):
    """Tests for build_list command."""
    
    def setUp(self):
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
            status='success',
            image_tag='test:abc123'
        )
    
    def test_list_builds(self):
        """Test listing builds."""
        out = StringIO()
        call_command('build_list', stdout=out)
        output = out.getvalue()
        
        self.assertIn('test-repo', output)
        self.assertIn('success', output)
    
    def test_list_builds_by_status(self):
        """Test filtering builds by status."""
        Build.objects.create(
            repository=self.repo,
            commit=self.commit,
            branch_name='main',
            status='failed'
        )
        
        out = StringIO()
        call_command('build_list', '--status=success', stdout=out)
        output = out.getvalue()
        
        self.assertIn('success', output)
        # Only 1 build should match
        self.assertIn('Found 1', output)
    
    def test_list_builds_json(self):
        """Test listing builds in JSON format."""
        out = StringIO()
        call_command('build_list', '--format=json', stdout=out)
        output = out.getvalue()
        
        data = json.loads(output)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['status'], 'success')


class BuildDetailCommandTest(TestCase):
    """Tests for build_detail command."""
    
    def setUp(self):
        self.repo = GitRepository.objects.create(
            name='test-repo',
            url='https://github.com/test/repo.git'
        )
        self.commit = Commit.objects.create(
            repository=self.repo,
            sha='abc123def456',
            message='Test commit message',
            author='Test Author',
            author_email='test@example.com',
            committed_at=timezone.now()
        )
        self.build = Build.objects.create(
            repository=self.repo,
            commit=self.commit,
            branch_name='main',
            status='success',
            image_tag='test:abc123',
            logs='Build completed successfully'
        )
    
    def test_build_detail(self):
        """Test getting build details."""
        out = StringIO()
        call_command('build_detail', str(self.build.id), stdout=out)
        output = out.getvalue()
        
        self.assertIn('test-repo', output)
        self.assertIn('success', output)
        self.assertIn('abc123de', output)
    
    def test_build_detail_with_logs(self):
        """Test getting build details with logs."""
        out = StringIO()
        call_command('build_detail', str(self.build.id), '--show-logs', stdout=out)
        output = out.getvalue()
        
        self.assertIn('Build completed successfully', output)
    
    def test_build_detail_json(self):
        """Test getting build details in JSON format."""
        out = StringIO()
        call_command('build_detail', str(self.build.id), '--format=json', stdout=out)
        output = out.getvalue()
        
        data = json.loads(output)
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['repository']['name'], 'test-repo')
    
    def test_build_detail_nonexistent(self):
        """Test getting details for non-existent build."""
        out = StringIO()
        with self.assertRaises(CommandError) as context:
            call_command('build_detail', '9999', stdout=out)
        
        self.assertIn('not found', str(context.exception))


class BuildCreateCommandTest(TestCase):
    """Tests for build_create command."""
    
    def setUp(self):
        self.repo = GitRepository.objects.create(
            name='test-repo',
            url='https://github.com/test/repo.git',
            default_branch='main'
        )
        self.branch = Branch.objects.create(
            repository=self.repo,
            name='main',
            commit_sha='abc123'
        )
        self.commit = Commit.objects.create(
            repository=self.repo,
            branch=self.branch,
            sha='abc123def456',
            message='Test commit',
            author='Test Author',
            author_email='test@example.com',
            committed_at=timezone.now()
        )
    
    @patch('builds.management.commands.build_create.execute_build')
    def test_create_build(self, mock_execute):
        """Test creating a build."""
        out = StringIO()
        call_command(
            'build_create',
            str(self.repo.id),
            '--commit=abc123',
            '--no-wait',
            stdout=out
        )
        output = out.getvalue()
        
        self.assertIn('created', output)
        self.assertTrue(Build.objects.filter(repository=self.repo).exists())
    
    def test_create_build_nonexistent_repo(self):
        """Test creating build for non-existent repository."""
        out = StringIO()
        with self.assertRaises(CommandError) as context:
            call_command('build_create', '9999', stdout=out)
        
        self.assertIn('not found', str(context.exception))


class ContainerListCommandTest(TestCase):
    """Tests for container_list command."""
    
    def setUp(self):
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
            status='success',
            image_tag='test:abc123',
            container_status='running',
            container_id='abc123container',
            host_port=8080
        )
    
    def test_list_containers(self):
        """Test listing containers."""
        out = StringIO()
        call_command('container_list', stdout=out)
        output = out.getvalue()
        
        self.assertIn('test-repo', output)
        self.assertIn('running', output)
        self.assertIn('8080', output)
    
    def test_list_running_only(self):
        """Test listing only running containers."""
        Build.objects.create(
            repository=self.repo,
            commit=self.commit,
            branch_name='main',
            status='success',
            container_status='stopped'
        )
        
        out = StringIO()
        call_command('container_list', '--running-only', stdout=out)
        output = out.getvalue()
        
        self.assertIn('running', output)
        self.assertIn('Found 1', output)
    
    def test_list_containers_json(self):
        """Test listing containers in JSON format."""
        out = StringIO()
        call_command('container_list', '--format=json', stdout=out)
        output = out.getvalue()
        
        data = json.loads(output)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['container_status'], 'running')


class ContainerStartCommandTest(TestCase):
    """Tests for container_start command."""
    
    def setUp(self):
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
            status='success',
            image_tag='test:abc123'
        )
    
    @patch('builds.management.commands.container_start.start_container')
    def test_start_container(self, mock_start):
        """Test starting a container."""
        mock_start.return_value = ('newcontainer123', 49152)
        
        out = StringIO()
        call_command('container_start', str(self.build.id), stdout=out)
        output = out.getvalue()
        
        self.assertIn('started successfully', output)
        self.assertIn('49152', output)
        
        self.build.refresh_from_db()
        self.assertEqual(self.build.container_status, 'running')
        self.assertEqual(self.build.host_port, 49152)
    
    def test_start_failed_build(self):
        """Test that starting container for failed build raises error."""
        self.build.status = 'failed'
        self.build.save()
        
        out = StringIO()
        with self.assertRaises(CommandError) as context:
            call_command('container_start', str(self.build.id), stdout=out)
        
        self.assertIn('successful builds', str(context.exception))
    
    def test_start_already_running(self):
        """Test that starting already running container raises error."""
        self.build.container_status = 'running'
        self.build.host_port = 8080
        self.build.save()
        
        out = StringIO()
        with self.assertRaises(CommandError) as context:
            call_command('container_start', str(self.build.id), stdout=out)
        
        self.assertIn('already running', str(context.exception))


class ContainerStopCommandTest(TestCase):
    """Tests for container_stop command."""
    
    def setUp(self):
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
            status='success',
            image_tag='test:abc123',
            container_status='running',
            container_id='runningcontainer123',
            host_port=8080
        )
    
    @patch('builds.management.commands.container_stop.stop_container')
    @patch('builds.management.commands.container_stop.remove_container')
    def test_stop_container(self, mock_remove, mock_stop):
        """Test stopping a container."""
        out = StringIO()
        call_command('container_stop', str(self.build.id), stdout=out)
        output = out.getvalue()
        
        self.assertIn('stopped successfully', output)
        
        self.build.refresh_from_db()
        self.assertEqual(self.build.container_status, 'stopped')
        self.assertEqual(self.build.container_id, '')
    
    def test_stop_no_container(self):
        """Test stopping when no container exists."""
        self.build.container_id = ''
        self.build.save()
        
        out = StringIO()
        with self.assertRaises(CommandError) as context:
            call_command('container_stop', str(self.build.id), stdout=out)
        
        self.assertIn('No container', str(context.exception))


class ContainerLogsCommandTest(TestCase):
    """Tests for container_logs command."""
    
    def setUp(self):
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
            status='success',
            container_status='running',
            container_id='runningcontainer123',
            host_port=8080
        )
    
    @patch('builds.management.commands.container_logs.get_container_logs')
    @patch('builds.management.commands.container_logs.get_container_status')
    def test_get_logs(self, mock_status, mock_logs):
        """Test getting container logs."""
        mock_logs.return_value = 'Log line 1\nLog line 2'
        mock_status.return_value = 'running'
        
        out = StringIO()
        call_command('container_logs', str(self.build.id), stdout=out)
        output = out.getvalue()
        
        self.assertIn('Log line 1', output)
        self.assertIn('Log line 2', output)
    
    @patch('builds.management.commands.container_logs.get_container_logs')
    @patch('builds.management.commands.container_logs.get_container_status')
    def test_get_logs_json(self, mock_status, mock_logs):
        """Test getting container logs in JSON format."""
        mock_logs.return_value = 'Test log output'
        mock_status.return_value = 'running'
        
        out = StringIO()
        call_command('container_logs', str(self.build.id), '--format=json', stdout=out)
        output = out.getvalue()
        
        data = json.loads(output)
        self.assertEqual(data['logs'], 'Test log output')
        self.assertEqual(data['status'], 'running')
    
    def test_get_logs_no_container(self):
        """Test getting logs when no container exists."""
        self.build.container_id = ''
        self.build.save()
        
        out = StringIO()
        with self.assertRaises(CommandError) as context:
            call_command('container_logs', str(self.build.id), stdout=out)
        
        self.assertIn('No container', str(context.exception))
