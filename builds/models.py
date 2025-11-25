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

