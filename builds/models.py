from django.db import models
from projects.models import GitRepository, Commit
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

# Directory containing Dockerfile templates
DOCKERFILE_TEMPLATES_DIR = Path(__file__).parent / 'dockerfile_templates'


def get_dockerfile_templates():
    """
    Load all Dockerfile templates from the templates directory.
    Returns a dictionary of {template_name: template_content}, sorted alphabetically by name.
    """
    templates = {}
    
    if DOCKERFILE_TEMPLATES_DIR.exists():
        for file_path in DOCKERFILE_TEMPLATES_DIR.glob('*.dockerfile'):
            # Use filename without extension as template name
            template_name = file_path.stem
            try:
                with open(file_path, 'r') as f:
                    templates[template_name] = f.read()
            except (IOError, OSError) as e:
                logger.warning(f"Failed to read Dockerfile template '{template_name}': {e}")
    
    # Return templates sorted alphabetically by name
    return dict(sorted(templates.items()))


def get_env_templates():
    """
    Load all .env templates from the templates directory.
    Returns a dictionary of {template_name: template_content}, sorted alphabetically by name.
    """
    templates = {}
    
    if DOCKERFILE_TEMPLATES_DIR.exists():
        for file_path in DOCKERFILE_TEMPLATES_DIR.glob('*.env'):
            # Use filename without extension as template name
            template_name = file_path.stem
            try:
                with open(file_path, 'r') as f:
                    templates[template_name] = f.read()
            except (IOError, OSError) as e:
                logger.warning(f"Failed to read .env template '{template_name}': {e}")
    
    # Return templates sorted alphabetically by name
    return dict(sorted(templates.items()))


def get_default_env_template():
    """Get the default .env template (Python)."""
    templates = get_env_templates()
    return templates.get('Python', DEFAULT_ENV_TEMPLATE)


# Default .env template (fallback)
DEFAULT_ENV_TEMPLATE = """# Environment Variables
# Add your environment variables here

DEBUG=True
"""


def get_template_choices():
    """
    Get template choices for use in forms/models.
    Returns a list of tuples [(template_name, template_name), ...]
    """
    templates = get_dockerfile_templates()
    return [(name, name) for name in sorted(templates.keys())]


def get_default_template():
    """Get the default Dockerfile template (Python)."""
    templates = get_dockerfile_templates()
    return templates.get('Python', DEFAULT_DOCKERFILE_TEMPLATE)


# Default Dockerfile template for auto-generation (fallback)
DEFAULT_DOCKERFILE_TEMPLATE = """# Auto-generated Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt* ./
RUN pip install --no-cache-dir -r requirements.txt || true

# Copy application code
COPY . .

# Expose the application port
EXPOSE 8080

# Default command (customize as needed)
CMD ["python", "-m", "http.server", "8080"]
"""


# Template-specific commands configuration
TEMPLATE_COMMANDS = {
    'Django': [
        {
            'name': 'Run Tests',
            'command': 'python manage.py test',
            'description': 'Run Django test suite',
            'icon': 'ti-test-pipe'
        },
        {
            'name': 'Run Migrations',
            'command': 'python manage.py migrate --noinput',
            'description': 'Apply database migrations',
            'icon': 'ti-database'
        },
        {
            'name': 'Create Superuser',
            'command': 'python manage.py createsuperuser --noinput --username admin --email admin@example.com || echo "Superuser already exists"',
            'description': 'Create admin user (username: admin)',
            'icon': 'ti-user-plus'
        },
        {
            'name': 'Collect Static',
            'command': 'python manage.py collectstatic --noinput',
            'description': 'Collect static files',
            'icon': 'ti-folder'
        },
        {
            'name': 'Check Deployment',
            'command': 'python manage.py check --deploy',
            'description': 'Check deployment configuration',
            'icon': 'ti-checklist'
        },
    ],
    'Flask': [
        {
            'name': 'Run Tests',
            'command': 'python -m pytest -v',
            'description': 'Run Flask test suite',
            'icon': 'ti-test-pipe'
        },
        {
            'name': 'Check Dependencies',
            'command': 'pip list',
            'description': 'List installed packages',
            'icon': 'ti-package'
        },
    ],
    'FastAPI': [
        {
            'name': 'Run Tests',
            'command': 'pytest -v',
            'description': 'Run FastAPI test suite',
            'icon': 'ti-test-pipe'
        },
        {
            'name': 'Check Dependencies',
            'command': 'pip list',
            'description': 'List installed packages',
            'icon': 'ti-package'
        },
    ],
    'React': [
        {
            'name': 'Run Tests',
            'command': 'npm test -- --watchAll=false',
            'description': 'Run React test suite',
            'icon': 'ti-test-pipe'
        },
        {
            'name': 'Build Production',
            'command': 'npm run build',
            'description': 'Build for production',
            'icon': 'ti-package'
        },
        {
            'name': 'List Dependencies',
            'command': 'npm list --depth=0',
            'description': 'List installed packages',
            'icon': 'ti-list'
        },
    ],
    'Node.js': [
        {
            'name': 'Run Tests',
            'command': 'npm test',
            'description': 'Run Node.js test suite',
            'icon': 'ti-test-pipe'
        },
        {
            'name': 'Run Lint',
            'command': 'npm run lint || echo "No lint script found"',
            'description': 'Run linter',
            'icon': 'ti-checklist'
        },
        {
            'name': 'Check Version',
            'command': 'node --version && npm --version',
            'description': 'Show Node and npm versions',
            'icon': 'ti-info-circle'
        },
    ],
    'Python': [
        {
            'name': 'Run Tests',
            'command': 'python -m pytest -v',
            'description': 'Run Python test suite',
            'icon': 'ti-test-pipe'
        },
        {
            'name': 'Check Dependencies',
            'command': 'pip list',
            'description': 'List installed packages',
            'icon': 'ti-package'
        },
        {
            'name': 'Python Version',
            'command': 'python --version',
            'description': 'Show Python version',
            'icon': 'ti-info-circle'
        },
    ],
    'Go': [
        {
            'name': 'Run Tests',
            'command': 'go test ./... -v',
            'description': 'Run Go test suite',
            'icon': 'ti-test-pipe'
        },
        {
            'name': 'Go Version',
            'command': 'go version',
            'description': 'Show Go version',
            'icon': 'ti-info-circle'
        },
        {
            'name': 'List Modules',
            'command': 'go list -m all',
            'description': 'List Go modules',
            'icon': 'ti-list'
        },
    ],
    'Static HTML': [],  # No commands for static sites
}


def detect_template_from_dockerfile(dockerfile_content: str) -> str:
    """
    Detect the template type from Dockerfile content.
    Returns the template name or 'Python' as fallback.
    """
    content_lower = dockerfile_content.lower()
    
    # Check for specific markers in the Dockerfile
    if 'django' in content_lower or 'manage.py' in content_lower:
        return 'Django'
    elif 'flask' in content_lower:
        return 'Flask'
    elif 'fastapi' in content_lower or 'uvicorn' in content_lower:
        return 'FastAPI'
    elif 'from node:' in content_lower and 'react' in content_lower:
        return 'React'
    elif 'from node:' in content_lower:
        return 'Node.js'
    elif 'from golang:' in content_lower or 'from go:' in content_lower:
        return 'Go'
    elif 'from nginx' in content_lower and 'html' in content_lower:
        return 'Static HTML'
    elif 'from python:' in content_lower:
        return 'Python'
    
    # Default fallback
    return 'Python'


def get_template_commands(template_name: str) -> list:
    """
    Get available commands for a specific template.
    Returns a list of command dictionaries.
    """
    return TEMPLATE_COMMANDS.get(template_name, [])


class Build(models.Model):
    """
    Represents a build request and its execution status.
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('running', 'Running'),
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]

    CONTAINER_STATUS_CHOICES = [
        ('none', 'Not Started'),
        ('starting', 'Starting'),
        ('running', 'Running'),
        ('stopped', 'Stopped'),
        ('error', 'Error'),
    ]

    DOCKERFILE_SOURCE_CHOICES = [
        ('generated', 'Auto-generated'),
        ('custom', 'Custom Content'),
        ('repo_file', 'File from Repository'),
    ]

    repository = models.ForeignKey(GitRepository, on_delete=models.CASCADE, related_name='builds')
    commit = models.ForeignKey(Commit, on_delete=models.CASCADE, related_name='builds')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Build metadata
    branch_name = models.CharField(max_length=255, help_text="Branch name at build time")
    image_tag = models.CharField(max_length=255, blank=True, help_text="Generated Docker image tag")
    
    # Dockerfile configuration
    dockerfile_source = models.CharField(
        max_length=20, 
        choices=DOCKERFILE_SOURCE_CHOICES, 
        default='generated',
        help_text="Source of the Dockerfile"
    )
    dockerfile_content = models.TextField(
        blank=True,
        default=DEFAULT_DOCKERFILE_TEMPLATE,
        help_text="Custom Dockerfile content"
    )
    dockerfile_path = models.CharField(
        max_length=255,
        blank=True,
        default='Dockerfile',
        help_text="Path to Dockerfile in repository"
    )
    
    # Environment configuration
    env_content = models.TextField(
        blank=True,
        default='',
        help_text="Environment variables content (.env file)"
    )
    
    # Logs and output
    logs = models.TextField(blank=True, help_text="Build logs")
    error_message = models.TextField(blank=True, help_text="Error message if failed")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Build configuration
    push_to_registry = models.BooleanField(default=False, help_text="Whether to push image to registry")
    deploy_after_build = models.BooleanField(default=False, help_text="Whether to deploy after successful build")
    
    # Container configuration
    container_port = models.IntegerField(default=8080, help_text="Port to expose from the container")
    host_port = models.IntegerField(null=True, blank=True, help_text="Host port mapped to container port")
    container_id = models.CharField(max_length=64, blank=True, help_text="Docker container ID when running")
    container_status = models.CharField(max_length=20, choices=CONTAINER_STATUS_CHOICES, default='none')

    class Meta:
        verbose_name = "Build"
        verbose_name_plural = "Builds"
        ordering = ['-created_at']

    def __str__(self) -> str:
        return f"Build #{self.id} - {self.repository.name} @ {self.commit.sha[:8]} ({self.status})"

    @property
    def duration(self) -> str:
        """Calculate build duration."""
        if self.started_at and self.completed_at:
            delta = self.completed_at - self.started_at
            total_seconds = int(delta.total_seconds())
            minutes, seconds = divmod(total_seconds, 60)
            return f"{minutes}m {seconds}s"
        return "N/A"

    @property
    def container_url(self) -> str:
        """Return the URL to access the running container."""
        if self.container_status == 'running' and self.host_port:
            return f"http://localhost:{self.host_port}"
        return ""

    @property
    def detected_template(self) -> str:
        """
        Detect and return the template type from the Dockerfile content.
        Returns the template name (e.g., 'Django', 'Flask', 'React', etc.)
        """
        if self.dockerfile_content:
            return detect_template_from_dockerfile(self.dockerfile_content)
        return 'Python'

    @property
    def available_commands(self) -> list:
        """
        Get available commands for this build based on its detected template.
        Returns a list of command dictionaries.
        """
        template = self.detected_template
        return get_template_commands(template)

    def sync_container_status(self) -> bool:
        """
        Synchronize container status with actual Docker state.
        Returns True if status was updated, False otherwise.
        """
        import docker
        
        if not self.container_id:
            # No container ID, nothing to sync
            if self.container_status != 'none':
                self.container_status = 'none'
                self.save(update_fields=['container_status'])
                logger.info(f"Build #{self.id}: Reset container status to 'none' (no container_id)")
                return True
            return False
        
        try:
            client = docker.from_env()
            try:
                container = client.containers.get(self.container_id)
                # Container exists, check its status
                docker_status = container.status.lower()  # 'running', 'exited', 'paused', etc.
                
                # Map Docker status to our container_status
                if docker_status == 'running':
                    new_status = 'running'
                elif docker_status in ['exited', 'dead']:
                    new_status = 'stopped'
                elif docker_status in ['created', 'restarting']:
                    new_status = 'starting'
                else:
                    new_status = 'error'
                
                if self.container_status != new_status:
                    old_status = self.container_status
                    self.container_status = new_status
                    self.save(update_fields=['container_status'])
                    logger.info(f"Build #{self.id}: Container status updated from '{old_status}' to '{new_status}'")
                    return True
                    
            except docker.errors.NotFound:
                # Container no longer exists
                if self.container_status != 'stopped':
                    self.container_status = 'stopped'
                    self.container_id = ''
                    self.save(update_fields=['container_status', 'container_id'])
                    logger.info(f"Build #{self.id}: Container no longer exists, status set to 'stopped'")
                    return True
                    
        except Exception as e:
            logger.error(f"Build #{self.id}: Error syncing container status: {e}")
            if self.container_status != 'error':
                self.container_status = 'error'
                self.save(update_fields=['container_status'])
                return True
        
        return False

