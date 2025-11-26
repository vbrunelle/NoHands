"""
Management command to stop a container.
"""
from django.core.management.base import BaseCommand, CommandError
from builds.models import Build
from builds.docker_utils import stop_container, remove_container, DockerError


class Command(BaseCommand):
    help = 'Stop a running container'

    def add_arguments(self, parser):
        parser.add_argument(
            'build_id',
            type=int,
            help='Build ID',
        )
        parser.add_argument(
            '--no-remove',
            action='store_true',
            help='Do not remove the container after stopping',
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
            build = Build.objects.get(id=build_id)
        except Build.DoesNotExist:
            raise CommandError(f"Build #{build_id} not found.")
        
        if not build.container_id:
            raise CommandError(f"No container to stop for build #{build_id}.")
        
        container_id = build.container_id
        
        try:
            self.stdout.write(f'Stopping container {container_id[:12]}...')
            stop_container(container_id)
            
            if not options['no_remove']:
                self.stdout.write(f'Removing container {container_id[:12]}...')
                remove_container(container_id)
            
            build.container_status = 'stopped'
            build.container_id = ''
            build.host_port = None
            build.save()
            
            if options['format'] == 'json':
                import json
                result = {
                    'build_id': build.id,
                    'container_id': container_id[:12],
                    'status': 'stopped',
                    'removed': not options['no_remove'],
                }
                self.stdout.write(json.dumps(result, indent=2))
            else:
                self.stdout.write(self.style.SUCCESS(f'\n✓ Container stopped successfully!'))
                if not options['no_remove']:
                    self.stdout.write(f'  Container {container_id[:12]} has been removed.')
                    
        except DockerError as e:
            raise CommandError(f"Failed to stop container: {e}")
