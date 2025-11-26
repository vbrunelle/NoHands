"""
Management command to start a container.
"""
import os
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from builds.models import Build
from builds.docker_utils import start_container, load_image_from_tar, DockerError


class Command(BaseCommand):
    help = 'Start a container for a successful build'

    def add_arguments(self, parser):
        parser.add_argument(
            'build_id',
            type=int,
            help='Build ID',
        )
        parser.add_argument(
            '--host-port',
            type=int,
            help='Host port to map to container (auto-assigned if not specified)',
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
        
        if build.status != 'success':
            raise CommandError(f"Can only start containers for successful builds. Build #{build_id} status is '{build.status}'.")
        
        if build.container_status == 'running':
            raise CommandError(f"Container is already running on port {build.host_port}.")
        
        try:
            # Determine the image tag to use
            image_tag = build.image_tag
            
            # If the build was local (not pushed to registry), try to load from tar
            if not build.push_to_registry and build.image_tag:
                image_name = build.repository.name.lower().replace(' ', '-')
                commit_tag = build.commit.sha[:8]
                tar_path = settings.GIT_CHECKOUT_DIR / 'builds' / f"build_{build.id}" / f"{image_name}_{commit_tag}.tar"
                
                if os.path.exists(tar_path):
                    self.stdout.write(f'Loading image from {tar_path}...')
                    image_tag = load_image_from_tar(str(tar_path))
            
            build.container_status = 'starting'
            build.save()
            
            self.stdout.write(f'Starting container for build #{build_id}...')
            
            container_name = f"nohands-build-{build.id}"
            container_id, host_port = start_container(
                image_tag=image_tag,
                container_port=build.container_port,
                host_port=options.get('host_port'),
                container_name=container_name,
            )
            
            build.container_id = container_id
            build.host_port = host_port
            build.container_status = 'running'
            build.save()
            
            if options['format'] == 'json':
                import json
                result = {
                    'build_id': build.id,
                    'container_id': container_id,
                    'host_port': host_port,
                    'container_port': build.container_port,
                    'status': 'running',
                    'url': f'http://localhost:{host_port}',
                }
                self.stdout.write(json.dumps(result, indent=2))
            else:
                self.stdout.write(self.style.SUCCESS(f'\n✓ Container started successfully!'))
                self.stdout.write(f'\n  Container ID: {container_id[:12]}')
                self.stdout.write(f'  Host Port: {host_port}')
                self.stdout.write(f'  Container Port: {build.container_port}')
                self.stdout.write(self.style.SUCCESS(f'  URL: http://localhost:{host_port}'))
                
        except DockerError as e:
            build.container_status = 'error'
            build.save()
            raise CommandError(f"Failed to start container: {e}")
