"""
Management command to list containers.
"""
from django.core.management.base import BaseCommand
from builds.models import Build


class Command(BaseCommand):
    help = 'List all containers (successful builds)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--running-only',
            action='store_true',
            help='Show only running containers',
        )
        parser.add_argument(
            '--format',
            type=str,
            choices=['table', 'json'],
            default='table',
            help='Output format (default: table)',
        )

    def handle(self, *args, **options):
        queryset = Build.objects.select_related('repository', 'commit').filter(status='success')
        
        if options['running_only']:
            queryset = queryset.filter(container_status='running')
        
        queryset = queryset.order_by('-created_at')
        
        if not queryset.exists():
            self.stdout.write(self.style.WARNING('No containers found.'))
            return
        
        if options['format'] == 'json':
            import json
            containers = []
            for build in queryset:
                containers.append({
                    'build_id': build.id,
                    'repository': build.repository.name,
                    'commit_sha': build.commit.sha[:8],
                    'branch_name': build.branch_name,
                    'image_tag': build.image_tag,
                    'container_status': build.container_status,
                    'container_id': build.container_id,
                    'host_port': build.host_port,
                    'container_port': build.container_port,
                    'url': build.container_url,
                })
            self.stdout.write(json.dumps(containers, indent=2))
        else:
            self.stdout.write(self.style.SUCCESS(f'\nFound {queryset.count()} container(s):\n'))
            self.stdout.write(f'{"Build":<8} {"Repository":<25} {"Commit":<10} {"Status":<12} {"Port":<10} {"URL"}')
            self.stdout.write('-' * 100)
            for build in queryset:
                status_style = {
                    'running': self.style.SUCCESS,
                    'stopped': self.style.WARNING,
                    'error': self.style.ERROR,
                    'none': lambda x: x,
                }.get(build.container_status, lambda x: x)
                
                port_info = str(build.host_port) if build.host_port else '-'
                url = build.container_url or '-'
                
                # Format status with padding before applying color to avoid ANSI code width issues
                status_padded = f'{build.container_status:<12}'
                
                self.stdout.write(
                    f'{build.id:<8} {build.repository.name:<25} {build.commit.sha[:8]:<10} '
                    f'{status_style(status_padded)} {port_info:<10} {url}'
                )
