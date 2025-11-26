"""
Management command to get container logs.
"""
from django.core.management.base import BaseCommand, CommandError
from builds.models import Build
from builds.docker_utils import get_container_logs, get_container_status, DockerError


class Command(BaseCommand):
    help = 'Get logs from a running container'

    def add_arguments(self, parser):
        parser.add_argument(
            'build_id',
            type=int,
            help='Build ID',
        )
        parser.add_argument(
            '--tail',
            type=int,
            default=100,
            help='Number of lines to show from the end (default: 100)',
        )
        parser.add_argument(
            '--format',
            type=str,
            choices=['plain', 'json'],
            default='plain',
            help='Output format (default: plain)',
        )

    def handle(self, *args, **options):
        build_id = options['build_id']
        
        try:
            build = Build.objects.get(id=build_id)
        except Build.DoesNotExist:
            raise CommandError(f"Build #{build_id} not found.")
        
        if not build.container_id:
            raise CommandError(f"No container found for build #{build_id}.")
        
        try:
            # Get logs
            logs = get_container_logs(build.container_id, tail=options['tail'])
            
            # Get current status
            status = get_container_status(build.container_id)
            
            # Update container status if changed
            if status == 'exited' and build.container_status == 'running':
                build.container_status = 'stopped'
                build.save()
            
            if options['format'] == 'json':
                import json
                result = {
                    'build_id': build.id,
                    'container_id': build.container_id[:12],
                    'status': status,
                    'logs': logs,
                }
                self.stdout.write(json.dumps(result, indent=2))
            else:
                self.stdout.write(f'Container: {build.container_id[:12]} (Status: {status})')
                self.stdout.write('-' * 50)
                if logs:
                    self.stdout.write(logs)
                else:
                    self.stdout.write(self.style.WARNING('No logs available.'))
                    
        except DockerError as e:
            raise CommandError(f"Failed to get container logs: {e}")
