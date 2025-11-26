"""
Management command to get build details.
"""
from django.core.management.base import BaseCommand, CommandError
from builds.models import Build


class Command(BaseCommand):
    help = 'Get details of a specific build'

    def add_arguments(self, parser):
        parser.add_argument(
            'build_id',
            type=int,
            help='Build ID',
        )
        parser.add_argument(
            '--show-logs',
            action='store_true',
            help='Show build logs',
        )
        parser.add_argument(
            '--format',
            type=str,
            choices=['table', 'json'],
            default='table',
            help='Output format (default: table)',
        )

    def handle(self, *args, **options):
        build_id = options['build_id']
        
        try:
            build = Build.objects.select_related('repository', 'commit').get(id=build_id)
        except Build.DoesNotExist:
            raise CommandError(f"Build #{build_id} not found.")
        
        if options['format'] == 'json':
            import json
            result = {
                'id': build.id,
                'repository': {
                    'id': build.repository.id,
                    'name': build.repository.name,
                },
                'commit': {
                    'sha': build.commit.sha,
                    'message': build.commit.message,
                    'author': build.commit.author,
                },
                'branch_name': build.branch_name,
                'status': build.status,
                'image_tag': build.image_tag,
                'duration': build.duration,
                'push_to_registry': build.push_to_registry,
                'container_port': build.container_port,
                'container_status': build.container_status,
                'container_id': build.container_id,
                'host_port': build.host_port,
                'created_at': build.created_at.isoformat() if build.created_at else None,
                'started_at': build.started_at.isoformat() if build.started_at else None,
                'completed_at': build.completed_at.isoformat() if build.completed_at else None,
                'error_message': build.error_message,
            }
            if options['show_logs']:
                result['logs'] = build.logs
            self.stdout.write(json.dumps(result, indent=2))
        else:
            status_style = {
                'pending': self.style.WARNING,
                'running': self.style.WARNING,
                'success': self.style.SUCCESS,
                'failed': self.style.ERROR,
                'cancelled': self.style.NOTICE,
            }.get(build.status, lambda x: x)
            
            self.stdout.write(f'\nBuild #{build.id}')
            self.stdout.write('=' * 50)
            self.stdout.write(f'Status: {status_style(build.status)}')
            self.stdout.write(f'\nRepository: {build.repository.name}')
            self.stdout.write(f'Branch: {build.branch_name}')
            self.stdout.write(f'Commit: {build.commit.sha[:8]}')
            self.stdout.write(f'Commit Message: {build.commit.message[:60]}...' if len(build.commit.message) > 60 else f'Commit Message: {build.commit.message}')
            self.stdout.write(f'Author: {build.commit.author}')
            
            self.stdout.write(f'\nConfiguration:')
            self.stdout.write(f'  Push to Registry: {"Yes" if build.push_to_registry else "No"}')
            self.stdout.write(f'  Container Port: {build.container_port}')
            self.stdout.write(f'  Dockerfile Source: {build.dockerfile_source}')
            
            self.stdout.write(f'\nTiming:')
            self.stdout.write(f'  Created: {build.created_at}')
            if build.started_at:
                self.stdout.write(f'  Started: {build.started_at}')
            if build.completed_at:
                self.stdout.write(f'  Completed: {build.completed_at}')
            self.stdout.write(f'  Duration: {build.duration}')
            
            if build.image_tag:
                self.stdout.write(f'\nImage Tag: {build.image_tag}')
            
            if build.container_status != 'none':
                self.stdout.write(f'\nContainer:')
                self.stdout.write(f'  Status: {build.container_status}')
                if build.container_id:
                    self.stdout.write(f'  Container ID: {build.container_id[:12]}')
                if build.host_port:
                    self.stdout.write(f'  Host Port: {build.host_port}')
                    self.stdout.write(f'  URL: http://localhost:{build.host_port}')
            
            if build.error_message:
                self.stdout.write(self.style.ERROR(f'\nError: {build.error_message}'))
            
            if options['show_logs'] and build.logs:
                self.stdout.write(f'\nBuild Logs:')
                self.stdout.write('-' * 50)
                self.stdout.write(build.logs)
