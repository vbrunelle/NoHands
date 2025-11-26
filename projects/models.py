from django.db import models
from django.contrib.auth.models import User
from pathlib import Path
from typing import Optional


class AppConfiguration(models.Model):
    """
    Singleton model to store application-wide configuration.
    Only one instance should exist.
    """
    app_url = models.URLField(
        max_length=500, 
        blank=True, 
        help_text="Base URL of the application (e.g., http://localhost:8000)"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Application Configuration"
        verbose_name_plural = "Application Configuration"

    def __str__(self) -> str:
        return f"App Configuration (URL: {self.app_url or 'Not set'})"

    def save(self, *args, **kwargs):
        """Ensure only one instance exists."""
        if not self.pk and AppConfiguration.objects.exists():
            # Update existing instance instead of creating new
            existing = AppConfiguration.objects.first()
            existing.app_url = self.app_url
            existing.save()
            # Set self.pk so caller gets a valid saved instance reference
            self.pk = existing.pk
            return
        super().save(*args, **kwargs)

    @classmethod
    def get_config(cls):
        """Get or create the singleton configuration instance."""
        config, _ = cls.objects.get_or_create(pk=1)
        return config


class GitRepository(models.Model):
    """
    Represents a Git repository that can be built and deployed.
    """
    name = models.CharField(max_length=255, unique=True, help_text="Repository name")
    url = models.CharField(max_length=500, help_text="Git repository URL or local path")
    description = models.TextField(blank=True, help_text="Repository description")
    default_branch = models.CharField(max_length=100, default='main', help_text="Default branch name")
    dockerfile_path = models.CharField(max_length=255, default='Dockerfile', help_text="Path to Dockerfile in repo")
    is_active = models.BooleanField(default=True, help_text="Whether this repository is active")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='repositories', help_text="User who connected this repository")
    github_id = models.CharField(max_length=100, blank=True, help_text="GitHub repository ID")

    class Meta:
        verbose_name = "Git Repository"
        verbose_name_plural = "Git Repositories"
        ordering = ['-created_at']

    def __str__(self) -> str:
        return self.name


class Branch(models.Model):
    """
    Represents a branch in a Git repository.
    """
    repository = models.ForeignKey(GitRepository, on_delete=models.CASCADE, related_name='branches')
    name = models.CharField(max_length=255, help_text="Branch name")
    commit_sha = models.CharField(max_length=40, help_text="Latest commit SHA on this branch")
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Branch"
        verbose_name_plural = "Branches"
        ordering = ['name']
        unique_together = [['repository', 'name']]

    def __str__(self) -> str:
        return f"{self.repository.name}/{self.name}"


class Commit(models.Model):
    """
    Represents a specific commit in a Git repository.
    """
    repository = models.ForeignKey(GitRepository, on_delete=models.CASCADE, related_name='commits')
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name='commits', null=True, blank=True)
    sha = models.CharField(max_length=40, help_text="Commit SHA")
    message = models.TextField(help_text="Commit message")
    author = models.CharField(max_length=255, help_text="Commit author")
    author_email = models.EmailField(help_text="Author email")
    committed_at = models.DateTimeField(help_text="Commit timestamp")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Commit"
        verbose_name_plural = "Commits"
        ordering = ['-committed_at']
        unique_together = [['repository', 'sha']]

    def __str__(self) -> str:
        return f"{self.sha[:8]} - {self.message[:50]}"


class AllowedHost(models.Model):
    """
    Stores allowed host domains for the application.
    
    These hosts are enforced after the initial server setup is complete.
    During first start (no users exist), any host is allowed, and the first
    host used during setup is automatically added to this list.
    """
    hostname = models.CharField(
        max_length=255,
        unique=True,
        help_text="Hostname or domain (e.g., 'localhost:8000', 'myapp.example.com')"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this host is currently allowed"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Allowed Host"
        verbose_name_plural = "Allowed Hosts"
        ordering = ['hostname']

    def __str__(self) -> str:
        status = "active" if self.is_active else "inactive"
        return f"{self.hostname} ({status})"

    @classmethod
    def get_all_active_hosts(cls):
        """Get all active allowed hosts as a list of hostnames."""
        return list(cls.objects.filter(is_active=True).values_list('hostname', flat=True))

    @classmethod
    def is_host_allowed(cls, hostname):
        """Check if a hostname is in the list of allowed hosts."""
        return cls.objects.filter(hostname=hostname, is_active=True).exists()

    @classmethod
    def add_host(cls, hostname):
        """Add a hostname to the allowed list if it doesn't exist."""
        obj, created = cls.objects.get_or_create(
            hostname=hostname,
            defaults={'is_active': True}
        )
        return obj, created

