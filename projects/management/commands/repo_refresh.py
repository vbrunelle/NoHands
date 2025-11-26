"""
Management command to refresh branches for a repository.
"""
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from projects.models import GitRepository, Branch
from projects.git_utils import clone_or_update_repo, list_branches, GitUtilsError


class Command(BaseCommand):
    help = 'Refresh branches for a Git repository'

    def add_arguments(self, parser):
        parser.add_argument(
            'repository',
            type=str,
            help='Repository ID or name',
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
        
        # Find repository by ID or name
        try:
            if repo_identifier.isdigit():
                repository = GitRepository.objects.get(id=int(repo_identifier))
            else:
                repository = GitRepository.objects.get(name=repo_identifier)
        except GitRepository.DoesNotExist:
            raise CommandError(f"Repository '{repo_identifier}' not found.")
        
        self.stdout.write(f'Refreshing branches for repository: {repository.name}')
        
        try:
            # Clone or update the repository
            repo_cache_path = settings.GIT_CHECKOUT_DIR / 'cache' / repository.name
            clone_or_update_repo(repository.url, repo_cache_path)
            
            # List branches
            branches_data = list_branches(repo_cache_path)
            
            # Update database
            for branch_data in branches_data:
                Branch.objects.update_or_create(
                    repository=repository,
                    name=branch_data['name'],
                    defaults={'commit_sha': branch_data['commit_sha']}
                )
            
            if options['format'] == 'json':
                import json
                branches = []
                for branch in repository.branches.all():
                    branches.append({
                        'id': branch.id,
                        'name': branch.name,
                        'commit_sha': branch.commit_sha,
                    })
                self.stdout.write(json.dumps(branches, indent=2))
            else:
                self.stdout.write(
                    self.style.SUCCESS(f'\n✓ Refreshed {len(branches_data)} branch(es):\n')
                )
                self.stdout.write(f'{"ID":<6} {"Branch Name":<40} {"Latest Commit"}')
                self.stdout.write('-' * 80)
                for branch in repository.branches.all().order_by('name'):
                    self.stdout.write(
                        f'{branch.id:<6} {branch.name:<40} {branch.commit_sha[:8]}'
                    )
                    
        except GitUtilsError as e:
            raise CommandError(f"Failed to refresh branches: {e}")
