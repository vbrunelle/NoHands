"""
Management command to list commits for a branch.
"""
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from projects.models import GitRepository, Branch, Commit
from projects.git_utils import clone_or_update_repo, list_commits, GitUtilsError


class Command(BaseCommand):
    help = 'List commits for a repository branch'

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
            '--limit',
            type=int,
            default=20,
            help='Maximum number of commits to display (default: 20)',
        )
        parser.add_argument(
            '--refresh',
            action='store_true',
            help='Refresh commits from Git before listing',
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
        
        # Get branch
        branch_name = options['branch'] or repository.default_branch
        
        try:
            branch = Branch.objects.get(repository=repository, name=branch_name)
        except Branch.DoesNotExist:
            raise CommandError(f"Branch '{branch_name}' not found. Run 'repo_refresh {repository.id}' first.")
        
        # Refresh commits if requested
        if options['refresh']:
            self.stdout.write(f'Refreshing commits for {repository.name}/{branch_name}...')
            try:
                repo_cache_path = settings.GIT_CHECKOUT_DIR / 'cache' / repository.name
                clone_or_update_repo(repository.url, repo_cache_path)
                commits_data = list_commits(repo_cache_path, branch_name, max_count=options['limit'])
                
                for commit_data in commits_data:
                    Commit.objects.update_or_create(
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
                raise CommandError(f"Failed to refresh commits: {e}")
        
        # Get commits from database
        commits = Commit.objects.filter(
            repository=repository,
            branch=branch
        ).order_by('-committed_at')[:options['limit']]
        
        if not commits.exists():
            self.stdout.write(self.style.WARNING(f'No commits found. Try running with --refresh option.'))
            return
        
        if options['format'] == 'json':
            import json
            result = []
            for commit in commits:
                result.append({
                    'id': commit.id,
                    'sha': commit.sha,
                    'message': commit.message,
                    'author': commit.author,
                    'author_email': commit.author_email,
                    'committed_at': commit.committed_at.isoformat() if commit.committed_at else None,
                })
            self.stdout.write(json.dumps(result, indent=2))
        else:
            self.stdout.write(self.style.SUCCESS(f'\nCommits for {repository.name}/{branch_name}:\n'))
            self.stdout.write(f'{"ID":<6} {"SHA":<10} {"Author":<20} {"Date":<20} {"Message"}')
            self.stdout.write('-' * 100)
            for commit in commits:
                date_str = commit.committed_at.strftime('%Y-%m-%d %H:%M') if commit.committed_at else 'N/A'
                message = commit.message[:40] + '...' if len(commit.message) > 40 else commit.message
                message = message.replace('\n', ' ')
                self.stdout.write(
                    f'{commit.id:<6} {commit.sha[:8]:<10} {commit.author[:18]:<20} {date_str:<20} {message}'
                )
