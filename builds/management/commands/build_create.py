"""
Management command to create a build.
"""
import threading
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from projects.models import GitRepository, Branch, Commit
from projects.git_utils import clone_or_update_repo, list_commits, GitUtilsError
from builds.models import Build, DEFAULT_DOCKERFILE_TEMPLATE
from builds.views import execute_build


class Command(BaseCommand):
    help = 'Create and start a build for a repository commit'

    def add_arguments(self, parser):
        parser.add_argument(
            'repository',
            type=str,
            help='Repository ID or name',
        )
        parser.add_argument(
            '--branch',
            type=str,
            help='Branch name (defaults to repository default branch)',
        )
        parser.add_argument(
            '--commit',
            type=str,
            help='Commit SHA (defaults to latest commit on branch)',
        )
        parser.add_argument(
            '--push-to-registry',
            action='store_true',
            help='Push the built image to the registry',
        )
        parser.add_argument(
            '--container-port',
            type=int,
            default=8080,
            help='Container port to expose (default: 8080)',
        )
        parser.add_argument(
            '--dockerfile-content',
            type=str,
            help='Custom Dockerfile content (inline)',
        )
        parser.add_argument(
            '--dockerfile-path',
            type=str,
            default='Dockerfile',
            help='Path to Dockerfile in repo (when using repo_file source)',
        )
        parser.add_argument(
            '--no-wait',
            action='store_true',
            help='Do not wait for build to complete (run in background)',
        )
        parser.add_argument(
            '--format',
            type=str,
            choices=['table', 'json'],
            default='table',
            help='Output format (default: table)',
        )

    def handle(self, *args, **options):
        repo_identifier = options['repository']
        
        # Find repository
        try:
            if repo_identifier.isdigit():
                repository = GitRepository.objects.get(id=int(repo_identifier))
            else:
                repository = GitRepository.objects.get(name=repo_identifier)
        except GitRepository.DoesNotExist:
            raise CommandError(f"Repository '{repo_identifier}' not found.")
        
        # Get branch
        branch_name = options['branch'] or repository.default_branch
        
        try:
            branch = Branch.objects.get(repository=repository, name=branch_name)
        except Branch.DoesNotExist:
            # Try to refresh branches first
            self.stdout.write(f'Branch "{branch_name}" not found. Refreshing branches...')
            try:
                repo_cache_path = settings.GIT_CHECKOUT_DIR / 'cache' / repository.name
                clone_or_update_repo(repository.url, repo_cache_path)
                from projects.git_utils import list_branches
                branches_data = list_branches(repo_cache_path)
                for bd in branches_data:
                    Branch.objects.update_or_create(
                        repository=repository,
                        name=bd['name'],
                        defaults={'commit_sha': bd['commit_sha']}
                    )
                branch = Branch.objects.get(repository=repository, name=branch_name)
            except (GitUtilsError, Branch.DoesNotExist) as e:
                raise CommandError(f"Branch '{branch_name}' not found in repository.")
        
        # Get commit
        commit_sha = options['commit']
        if commit_sha:
            try:
                commit = Commit.objects.get(repository=repository, sha__startswith=commit_sha)
            except Commit.DoesNotExist:
                raise CommandError(f"Commit '{commit_sha}' not found.")
            except Commit.MultipleObjectsReturned:
                raise CommandError(f"Ambiguous commit SHA '{commit_sha}'. Please provide more characters.")
        else:
            # Get latest commit on branch
            try:
                repo_cache_path = settings.GIT_CHECKOUT_DIR / 'cache' / repository.name
                clone_or_update_repo(repository.url, repo_cache_path)
                commits_data = list_commits(repo_cache_path, branch_name, max_count=1)
                if not commits_data:
                    raise CommandError(f"No commits found on branch '{branch_name}'.")
                
                commit_data = commits_data[0]
                commit, _ = Commit.objects.update_or_create(
                    repository=repository,
                    sha=commit_data['sha'],
                    defaults={
                        'branch': branch,
                        'message': commit_data['message'],
                        'author': commit_data['author'],
                        'author_email': commit_data['author_email'],
                        'committed_at': commit_data['committed_at']
                    }
                )
            except GitUtilsError as e:
                raise CommandError(f"Failed to get commits: {e}")
        
        # Determine Dockerfile configuration
        dockerfile_source = 'generated'
        dockerfile_content = DEFAULT_DOCKERFILE_TEMPLATE
        dockerfile_path = options['dockerfile_path']
        
        if options['dockerfile_content']:
            dockerfile_source = 'custom'
            dockerfile_content = options['dockerfile_content']
        elif dockerfile_path != 'Dockerfile':
            dockerfile_source = 'repo_file'
        
        # Create build
        build = Build.objects.create(
            repository=repository,
            commit=commit,
            branch_name=branch_name,
            status='pending',
            push_to_registry=options['push_to_registry'],
            container_port=options['container_port'],
            dockerfile_source=dockerfile_source,
            dockerfile_content=dockerfile_content,
            dockerfile_path=dockerfile_path,
        )
        
        self.stdout.write(self.style.SUCCESS(f'✓ Build #{build.id} created'))
        
        if options['no_wait']:
            # Start build in background thread
            thread = threading.Thread(target=execute_build, args=(build.id,))
            thread.daemon = True
            thread.start()
            self.stdout.write(f'Build started in background. Use "python manage.py build_detail {build.id}" to check status.')
        else:
            # Run build synchronously
            self.stdout.write('Starting build...')
            execute_build(build.id)
            
            # Refresh build status
            build.refresh_from_db()
            
            if options['format'] == 'json':
                import json
                result = {
                    'id': build.id,
                    'repository': build.repository.name,
                    'commit_sha': build.commit.sha[:8],
                    'branch_name': build.branch_name,
                    'status': build.status,
                    'image_tag': build.image_tag,
                    'duration': build.duration,
                    'error_message': build.error_message,
                }
                self.stdout.write(json.dumps(result, indent=2))
            else:
                status_style = self.style.SUCCESS if build.status == 'success' else self.style.ERROR
                self.stdout.write(status_style(f'\nBuild #{build.id} {build.status}'))
                self.stdout.write(f'  Repository: {build.repository.name}')
                self.stdout.write(f'  Commit: {build.commit.sha[:8]}')
                self.stdout.write(f'  Branch: {build.branch_name}')
                self.stdout.write(f'  Duration: {build.duration}')
                if build.image_tag:
                    self.stdout.write(f'  Image Tag: {build.image_tag}')
                if build.error_message:
                    self.stdout.write(self.style.ERROR(f'  Error: {build.error_message}'))
