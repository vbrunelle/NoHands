"""
Management command to list builds.
"""
from django.core.management.base import BaseCommand
from builds.models import Build


class Command(BaseCommand):
    help = 'List all builds'

    def add_arguments(self, parser):
        parser.add_argument(
            '--repository',
            type=str,
            help='Filter by repository ID or name',
        )
        parser.add_argument(
            '--status',
            type=str,
            choices=['pending', 'running', 'success', 'failed', 'cancelled'],
            help='Filter by build status',
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=20,
            help='Maximum number of builds to display (default: 20)',
        )
        parser.add_argument(
            '--format',
            type=str,
            choices=['table', 'json'],
            default='table',
            help='Output format (default: table)',
        )

    def handle(self, *args, **options):
        from projects.models import GitRepository
        
        queryset = Build.objects.select_related('repository', 'commit').all()
        
        # Filter by repository
        if options['repository']:
            repo_identifier = options['repository']
            try:
                if repo_identifier.isdigit():
                    repository = GitRepository.objects.get(id=int(repo_identifier))
                else:
                    repository = GitRepository.objects.get(name=repo_identifier)
                queryset = queryset.filter(repository=repository)
            except GitRepository.DoesNotExist:
                self.stdout.write(self.style.ERROR(f"Repository '{repo_identifier}' not found."))
                return
        
        # Filter by status
        if options['status']:
            queryset = queryset.filter(status=options['status'])
        
        queryset = queryset.order_by('-created_at')[:options['limit']]
        
        if not queryset.exists():
            self.stdout.write(self.style.WARNING('No builds found.'))
            return
        
        if options['format'] == 'json':
            import json
            builds = []
            for build in queryset:
                builds.append({
                    'id': build.id,
                    'repository': build.repository.name,
                    'commit_sha': build.commit.sha[:8],
                    'branch_name': build.branch_name,
                    'status': build.status,
                    'image_tag': build.image_tag,
                    'duration': build.duration,
                    'created_at': build.created_at.isoformat() if build.created_at else None,
                })
            self.stdout.write(json.dumps(builds, indent=2))
        else:
            self.stdout.write(self.style.SUCCESS(f'\nFound {len(queryset)} build(s):\n'))
            self.stdout.write(f'{"ID":<6} {"Repository":<25} {"Commit":<10} {"Branch":<20} {"Status":<10} {"Duration":<10}')
            self.stdout.write('-' * 100)
            for build in queryset:
                status_style = {
                    'pending': self.style.WARNING,
                    'running': self.style.WARNING,
                    'success': self.style.SUCCESS,
                    'failed': self.style.ERROR,
                    'cancelled': self.style.NOTICE,
                }.get(build.status, lambda x: x)
                
                # Format status with padding before applying color to avoid ANSI code width issues
                status_padded = f'{build.status:<10}'
                
                self.stdout.write(
                    f'{build.id:<6} {build.repository.name:<25} {build.commit.sha[:8]:<10} '
                    f'{build.branch_name[:18]:<20} {status_style(status_padded)} {build.duration:<10}'
                )
