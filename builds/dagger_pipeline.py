"""
Dagger pipeline for building and deploying Docker images.
"""
import asyncio
import logging
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime

import dagger
from dagger import DaggerError

logger = logging.getLogger(__name__)


class DaggerPipelineError(Exception):
    """Base exception for Dagger pipeline errors."""
    pass


class BuildResult:
    """Structured result from a Dagger build."""
    
    def __init__(
        self,
        status: str,
        image_tag: str = "",
        logs: str = "",
        error_message: str = "",
        duration: float = 0.0
    ):
        self.status = status
        self.image_tag = image_tag
        self.logs = logs
        self.error_message = error_message
        self.duration = duration
    
    def to_dict(self) -> Dict:
        """Convert result to dictionary."""
        return {
            'status': self.status,
            'image_tag': self.image_tag,
            'logs': self.logs,
            'error_message': self.error_message,
            'duration': self.duration
        }


async def build_docker_image(
    source_dir: Path,
    dockerfile_path: str,
    image_name: str,
    image_tag: str,
    push_to_registry: bool = False,
    registry_url: Optional[str] = None,
    registry_username: Optional[str] = None,
    registry_password: Optional[str] = None,
) -> BuildResult:
    """
    Build a Docker image using Dagger.
    
    Args:
        source_dir: Path to source code directory
        dockerfile_path: Path to Dockerfile relative to source_dir
        image_name: Name for the Docker image
        image_tag: Tag for the Docker image
        push_to_registry: Whether to push to registry
        registry_url: Docker registry URL
        registry_username: Registry username
        registry_password: Registry password
        
    Returns:
        BuildResult with build status and metadata
    """
    start_time = datetime.now()
    logs = []
    
    try:
        async with dagger.Connection() as client:
            logs.append(f"Starting build for {image_name}:{image_tag}")
            
            # Load the source directory
            source = client.host().directory(str(source_dir))
            
            # Build the container
            logs.append(f"Building image from {dockerfile_path}")
            container = source.docker_build(dockerfile=dockerfile_path)
            
            # Get the image reference
            full_image_tag = f"{image_name}:{image_tag}"
            
            if push_to_registry and registry_url and registry_username and registry_password:
                # Login to registry
                logs.append(f"Logging in to registry {registry_url}")
                registry_address = registry_url
                if not registry_address.startswith(('http://', 'https://')):
                    registry_address = f"https://{registry_address}"
                
                # Set registry authentication
                container = container.with_registry_auth(
                    address=registry_address,
                    username=registry_username,
                    secret=client.set_secret("registry_password", registry_password)
                )
                
                # Push to registry
                full_image_tag = f"{registry_url}/{image_name}:{image_tag}"
                logs.append(f"Pushing image to {full_image_tag}")
                ref = await container.publish(full_image_tag)
                logs.append(f"Successfully pushed image: {ref}")
            else:
                # Just build without pushing
                logs.append("Building image without pushing to registry")
                ref = await container.export(str(source_dir / f"{image_name}_{image_tag}.tar"))
                logs.append(f"Image built and exported to: {ref}")
                full_image_tag = f"{image_name}:{image_tag}"
            
            duration = (datetime.now() - start_time).total_seconds()
            logs.append(f"Build completed successfully in {duration:.2f} seconds")
            
            return BuildResult(
                status='success',
                image_tag=full_image_tag,
                logs='\n'.join(logs),
                duration=duration
            )
            
    except DaggerError as e:
        duration = (datetime.now() - start_time).total_seconds()
        error_msg = f"Dagger build failed: {str(e)}"
        logs.append(error_msg)
        logger.error(error_msg)
        
        return BuildResult(
            status='failed',
            logs='\n'.join(logs),
            error_message=error_msg,
            duration=duration
        )
    except Exception as e:
        duration = (datetime.now() - start_time).total_seconds()
        error_msg = f"Unexpected error during build: {str(e)}"
        logs.append(error_msg)
        logger.error(error_msg)
        
        return BuildResult(
            status='failed',
            logs='\n'.join(logs),
            error_message=error_msg,
            duration=duration
        )


def run_build_sync(
    source_dir: Path,
    dockerfile_path: str,
    image_name: str,
    image_tag: str,
    push_to_registry: bool = False,
    registry_url: Optional[str] = None,
    registry_username: Optional[str] = None,
    registry_password: Optional[str] = None,
) -> BuildResult:
    """
    Synchronous wrapper for building Docker images.
    
    This function creates an event loop and runs the async build function.
    Use this from Django views.
    """
    try:
        # Use asyncio.run() which properly manages the event loop lifecycle
        result = asyncio.run(
            build_docker_image(
                source_dir=source_dir,
                dockerfile_path=dockerfile_path,
                image_name=image_name,
                image_tag=image_tag,
                push_to_registry=push_to_registry,
                registry_url=registry_url,
                registry_username=registry_username,
                registry_password=registry_password,
            )
        )
        return result
    except Exception as e:
        error_msg = f"Failed to run build: {str(e)}"
        logger.error(error_msg)
        return BuildResult(
            status='failed',
            error_message=error_msg,
            logs=error_msg
        )
