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
    Returns a dictionary of {template_name: template_content}.
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
    
    return templates


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

