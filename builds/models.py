from django.db import models
from projects.models import GitRepository, Commit


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

    repository = models.ForeignKey(GitRepository, on_delete=models.CASCADE, related_name='builds')
    commit = models.ForeignKey(Commit, on_delete=models.CASCADE, related_name='builds')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Build metadata
    branch_name = models.CharField(max_length=255, help_text="Branch name at build time")
    image_tag = models.CharField(max_length=255, blank=True, help_text="Generated Docker image tag")
    
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

