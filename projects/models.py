from django.db import models
from pathlib import Path
from typing import Optional


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

