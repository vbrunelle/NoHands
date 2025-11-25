"""
Docker container management utilities.
"""
import logging
import subprocess
import socket
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


class DockerError(Exception):
    """Exception raised for Docker-related errors."""
    pass


def find_available_port(start_port: int = 8000, max_attempts: int = 100) -> int:
    """
    Find an available port on the host.
    
    Note: There's an inherent race condition between checking port availability
    and actually binding to it. The start_container function implements retry
    logic to handle this case.
    
    Args:
        start_port: Starting port number to check
        max_attempts: Maximum number of ports to try
        
    Returns:
        An available port number
        
    Raises:
        DockerError: If no available port is found
    """
    for port in range(start_port, start_port + max_attempts):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('localhost', port))
                return port
        except OSError:
            continue
    raise DockerError(f"No available port found between {start_port} and {start_port + max_attempts}")


def start_container(
    image_tag: str,
    container_port: int,
    host_port: Optional[int] = None,
    container_name: Optional[str] = None,
    max_retries: int = 3,
) -> Tuple[str, int]:
    """
    Start a Docker container from the given image.
    
    Args:
        image_tag: Docker image tag to run
        container_port: Port to expose from the container
        host_port: Host port to map to (if None, an available port will be found)
        container_name: Optional name for the container
        max_retries: Maximum number of retry attempts if port is taken
        
    Returns:
        Tuple of (container_id, host_port)
        
    Raises:
        DockerError: If container fails to start after all retries
    """
    last_error = None
    
    for attempt in range(max_retries):
        try:
            current_port = host_port if host_port is not None else find_available_port()
            
            cmd = [
                'docker', 'run',
                '-d',  # Detached mode
                '-p', f'{current_port}:{container_port}',
            ]
            
            if container_name:
                # Add attempt number to avoid name conflicts on retry
                name = container_name if attempt == 0 else f"{container_name}-{attempt}"
                cmd.extend(['--name', name])
            
            cmd.append(image_tag)
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode != 0:
                # Check if it's a port conflict error
                if 'port is already allocated' in result.stderr.lower() or 'bind' in result.stderr.lower():
                    last_error = DockerError(f"Port {current_port} is already in use")
                    continue
                raise DockerError(f"Failed to start container: {result.stderr}")
            
            container_id = result.stdout.strip()
            logger.info(f"Started container {container_id[:12]} on port {current_port}")
            return container_id, current_port
            
        except subprocess.TimeoutExpired:
            raise DockerError("Timeout while starting container")
        except FileNotFoundError:
            raise DockerError("Docker command not found. Is Docker installed?")
    
    # All retries exhausted
    if last_error:
        raise last_error
    raise DockerError("Failed to start container after multiple attempts")


def stop_container(container_id: str) -> bool:
    """
    Stop a running Docker container.
    
    Args:
        container_id: Docker container ID
        
    Returns:
        True if container was stopped successfully
        
    Raises:
        DockerError: If container fails to stop
    """
    try:
        result = subprocess.run(
            ['docker', 'stop', container_id],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode != 0:
            raise DockerError(f"Failed to stop container: {result.stderr}")
        
        logger.info(f"Stopped container {container_id[:12]}")
        return True
        
    except subprocess.TimeoutExpired:
        raise DockerError("Timeout while stopping container")
    except FileNotFoundError:
        raise DockerError("Docker command not found. Is Docker installed?")


def remove_container(container_id: str, force: bool = True) -> bool:
    """
    Remove a Docker container.
    
    Args:
        container_id: Docker container ID
        force: Force removal of running container
        
    Returns:
        True if container was removed successfully
        
    Raises:
        DockerError: If container fails to be removed
    """
    cmd = ['docker', 'rm']
    if force:
        cmd.append('-f')
    cmd.append(container_id)
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode != 0:
            raise DockerError(f"Failed to remove container: {result.stderr}")
        
        logger.info(f"Removed container {container_id[:12]}")
        return True
        
    except subprocess.TimeoutExpired:
        raise DockerError("Timeout while removing container")
    except FileNotFoundError:
        raise DockerError("Docker command not found. Is Docker installed?")


def get_container_logs(container_id: str, tail: Optional[int] = None) -> str:
    """
    Get logs from a Docker container.
    
    Args:
        container_id: Docker container ID
        tail: Number of lines to return from the end (None for all logs)
        
    Returns:
        Container logs as string
        
    Raises:
        DockerError: If logs cannot be retrieved
    """
    # Use --timestamps to help order the logs when combining stdout/stderr
    cmd = ['docker', 'logs', '--timestamps']
    if tail is not None:
        cmd.extend(['--tail', str(tail)])
    cmd.append(container_id)
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode != 0:
            raise DockerError(f"Failed to get container logs: {result.stderr}")
        
        # Docker logs writes stdout and stderr separately
        # When timestamps are enabled, we can sort them for proper ordering
        stdout_lines = result.stdout.splitlines() if result.stdout else []
        stderr_lines = result.stderr.splitlines() if result.stderr else []
        
        # Combine and sort by timestamp (timestamps are ISO format at start of each line)
        all_lines = stdout_lines + stderr_lines
        all_lines.sort()
        
        return '\n'.join(all_lines)
        
    except subprocess.TimeoutExpired:
        raise DockerError("Timeout while getting container logs")
    except FileNotFoundError:
        raise DockerError("Docker command not found. Is Docker installed?")


def get_container_status(container_id: str) -> str:
    """
    Get the status of a Docker container.
    
    Args:
        container_id: Docker container ID
        
    Returns:
        Container status ('running', 'exited', 'stopped', or 'unknown')
        
    Raises:
        DockerError: If status cannot be retrieved
    """
    try:
        result = subprocess.run(
            ['docker', 'inspect', '-f', '{{.State.Status}}', container_id],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode != 0:
            # Container might not exist
            return 'unknown'
        
        return result.stdout.strip()
        
    except subprocess.TimeoutExpired:
        raise DockerError("Timeout while checking container status")
    except FileNotFoundError:
        raise DockerError("Docker command not found. Is Docker installed?")


def load_image_from_tar(tar_path: str) -> str:
    """
    Load a Docker image from a tar file.
    
    Args:
        tar_path: Path to the tar file
        
    Returns:
        Image tag/ID
        
    Raises:
        DockerError: If image cannot be loaded
    """
    try:
        result = subprocess.run(
            ['docker', 'load', '-i', tar_path],
            capture_output=True,
            text=True,
            timeout=120
        )
        
        if result.returncode != 0:
            raise DockerError(f"Failed to load image: {result.stderr}")
        
        # Parse the image tag from output
        # Output can be like: "Loaded image: image_name:tag" or "Loaded image ID: sha256:..."
        output = result.stdout.strip()
        
        # Try to extract the image reference
        if 'Loaded image:' in output:
            # Format: "Loaded image: image_name:tag"
            image_ref = output.split('Loaded image:')[1].strip()
            logger.info(f"Loaded image from {tar_path}: {image_ref}")
            return image_ref
        elif 'Loaded image ID:' in output:
            # Format: "Loaded image ID: sha256:abc123..."
            # Need to get the actual image ID without the sha256: prefix for docker run
            image_id = output.split('Loaded image ID:')[1].strip()
            # Remove sha256: prefix if present
            if image_id.startswith('sha256:'):
                image_id = image_id[7:]
            logger.info(f"Loaded image from {tar_path}: {image_id}")
            return image_id
        else:
            # Fallback: return the whole output
            logger.warning(f"Unexpected docker load output format: {output}")
            return output
        
    except subprocess.TimeoutExpired:
        raise DockerError("Timeout while loading image")
    except FileNotFoundError:
        raise DockerError("Docker command not found. Is Docker installed?")
