"""
Management command to list all repositories.
"""
from django.core.management.base import BaseCommand
from projects.models import GitRepository


class Command(BaseCommand):
    help = 'List all Git repositories'

    def add_arguments(self, parser):
        parser.add_argument(
            '--active-only',
            action='store_true',
            help='Show only active repositories',
        )
        parser.add_argument(
            '--format',
            type=str,
            choices=['table', 'json'],
            default='table',
            help='Output format (default: table)',
        )

    def handle(self, *args, **options):
        queryset = GitRepository.objects.all()
        
        if options['active_only']:
            queryset = queryset.filter(is_active=True)
        
        queryset = queryset.order_by('name')
        
        if not queryset.exists():
            self.stdout.write(self.style.WARNING('No repositories found.'))
            return
        
        if options['format'] == 'json':
            import json
            repos = []
            for repo in queryset:
                repos.append({
                    'id': repo.id,
                    'name': repo.name,
                    'url': repo.url,
                    'default_branch': repo.default_branch,
                    'is_active': repo.is_active,
                    'description': repo.description,
                })
            self.stdout.write(json.dumps(repos, indent=2))
        else:
            self.stdout.write(self.style.SUCCESS(f'\nFound {queryset.count()} repository(ies):\n'))
            self.stdout.write(f'{"ID":<6} {"Name":<30} {"Default Branch":<15} {"Active":<8} {"URL"}')
            self.stdout.write('-' * 100)
            for repo in queryset:
                active = '✓' if repo.is_active else '✗'
                self.stdout.write(
                    f'{repo.id:<6} {repo.name:<30} {repo.default_branch:<15} {active:<8} {repo.url}'
                )
