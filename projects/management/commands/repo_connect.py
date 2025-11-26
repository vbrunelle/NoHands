"""
Management command to connect a repository.
"""
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from projects.models import GitRepository


class Command(BaseCommand):
    help = 'Connect a Git repository'

    def add_arguments(self, parser):
        parser.add_argument(
            'name',
            type=str,
            help='Repository name (unique identifier)',
        )
        parser.add_argument(
            'url',
            type=str,
            help='Git repository URL or local path',
        )
        parser.add_argument(
            '--description',
            type=str,
            default='',
            help='Repository description',
        )
        parser.add_argument(
            '--default-branch',
            type=str,
            default='main',
            help='Default branch name (default: main)',
        )
        parser.add_argument(
            '--dockerfile-path',
            type=str,
            default='Dockerfile',
            help='Path to Dockerfile in the repository (default: Dockerfile)',
        )
        parser.add_argument(
            '--inactive',
            action='store_true',
            help='Create repository as inactive',
        )
        parser.add_argument(
            '--github-id',
            type=str,
            default='',
            help='GitHub repository ID (optional)',
        )
        parser.add_argument(
            '--user',
            type=str,
            help='Username to associate with the repository (optional)',
        )

    def handle(self, *args, **options):
        name = options['name']
        url = options['url']
        
        # Check if repository already exists
        if GitRepository.objects.filter(name=name).exists():
            raise CommandError(f"Repository '{name}' already exists.")
        
        # Get user if specified
        user = None
        if options['user']:
            try:
                user = User.objects.get(username=options['user'])
            except User.DoesNotExist:
                raise CommandError(f"User '{options['user']}' not found.")
        
        # Create repository
        repo = GitRepository.objects.create(
            name=name,
            url=url,
            description=options['description'],
            default_branch=options['default_branch'],
            dockerfile_path=options['dockerfile_path'],
            is_active=not options['inactive'],
            github_id=options['github_id'],
            user=user,
        )
        
        self.stdout.write(
            self.style.SUCCESS(f"✓ Repository '{name}' created successfully!")
        )
        self.stdout.write(f'\nRepository details:')
        self.stdout.write(f'  ID: {repo.id}')
        self.stdout.write(f'  Name: {repo.name}')
        self.stdout.write(f'  URL: {repo.url}')
        self.stdout.write(f'  Default Branch: {repo.default_branch}')
        self.stdout.write(f'  Dockerfile Path: {repo.dockerfile_path}')
        self.stdout.write(f'  Active: {"Yes" if repo.is_active else "No"}')
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\nUse "python manage.py repo_refresh {repo.id}" to fetch branches.'
            )
        )
