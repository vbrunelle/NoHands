"""
Tests for Dockerfile configuration and validation.

These tests verify that the NoHands server Dockerfile is properly configured
and follows best practices for containerized Django applications.
"""

import os
import unittest
from pathlib import Path


class DockerfileTest(unittest.TestCase):
    """Tests for the NoHands server Dockerfile."""
    
    @classmethod
    def setUpClass(cls):
        """Set up test fixtures."""
        cls.project_root = Path(__file__).resolve().parent.parent
        cls.dockerfile_path = cls.project_root / 'Dockerfile'
        cls.dockerignore_path = cls.project_root / '.dockerignore'
        
        # Read Dockerfile content
        if cls.dockerfile_path.exists():
            with open(cls.dockerfile_path, 'r') as f:
                cls.dockerfile_content = f.read()
        else:
            cls.dockerfile_content = None
            
        # Read .dockerignore content
        if cls.dockerignore_path.exists():
            with open(cls.dockerignore_path, 'r') as f:
                cls.dockerignore_content = f.read()
        else:
            cls.dockerignore_content = None
    
    def test_dockerfile_exists(self):
        """Test that Dockerfile exists in project root."""
        self.assertTrue(
            self.dockerfile_path.exists(),
            "Dockerfile should exist in project root"
        )
    
    def test_dockerfile_not_empty(self):
        """Test that Dockerfile is not empty."""
        self.assertIsNotNone(self.dockerfile_content, "Dockerfile should exist")
        self.assertGreater(
            len(self.dockerfile_content.strip()),
            0,
            "Dockerfile should not be empty"
        )
    
    def test_dockerfile_uses_python_base_image(self):
        """Test that Dockerfile uses Python base image."""
        self.assertIn(
            'FROM python:',
            self.dockerfile_content,
            "Dockerfile should use Python base image"
        )
    
    def test_dockerfile_uses_specific_python_version(self):
        """Test that Dockerfile uses Python 3.11."""
        self.assertIn(
            'python:3.11',
            self.dockerfile_content,
            "Dockerfile should use Python 3.11"
        )
    
    def test_dockerfile_uses_slim_image(self):
        """Test that Dockerfile uses slim base image for smaller size."""
        self.assertIn(
            'slim',
            self.dockerfile_content,
            "Dockerfile should use slim variant for smaller image size"
        )
    
    def test_dockerfile_sets_workdir(self):
        """Test that Dockerfile sets WORKDIR."""
        self.assertIn(
            'WORKDIR /app',
            self.dockerfile_content,
            "Dockerfile should set WORKDIR to /app"
        )
    
    def test_dockerfile_copies_requirements(self):
        """Test that Dockerfile copies requirements.txt."""
        self.assertIn(
            'COPY requirements.txt',
            self.dockerfile_content,
            "Dockerfile should copy requirements.txt"
        )
    
    def test_dockerfile_installs_requirements(self):
        """Test that Dockerfile installs Python requirements."""
        self.assertIn(
            'pip install',
            self.dockerfile_content,
            "Dockerfile should install Python requirements"
        )
    
    def test_dockerfile_installs_git(self):
        """Test that Dockerfile installs Git (required for GitPython)."""
        self.assertIn(
            'git',
            self.dockerfile_content.lower(),
            "Dockerfile should install Git (required for GitPython)"
        )
    
    def test_dockerfile_exposes_port(self):
        """Test that Dockerfile exposes port 8000."""
        self.assertIn(
            'EXPOSE 8000',
            self.dockerfile_content,
            "Dockerfile should expose port 8000"
        )
    
    def test_dockerfile_has_cmd(self):
        """Test that Dockerfile has CMD instruction."""
        self.assertIn(
            'CMD',
            self.dockerfile_content,
            "Dockerfile should have CMD instruction"
        )
    
    def test_dockerfile_runs_migrate(self):
        """Test that Dockerfile runs migrations on startup."""
        self.assertIn(
            'migrate',
            self.dockerfile_content,
            "Dockerfile should run database migrations on startup"
        )
    
    def test_dockerfile_runs_server(self):
        """Test that Dockerfile runs Django server."""
        self.assertIn(
            'runserver',
            self.dockerfile_content,
            "Dockerfile should run Django development server"
        )
    
    def test_dockerfile_binds_to_all_interfaces(self):
        """Test that server binds to 0.0.0.0 for container access."""
        self.assertIn(
            '0.0.0.0:8000',
            self.dockerfile_content,
            "Server should bind to 0.0.0.0:8000 for container access"
        )
    
    def test_dockerfile_sets_python_unbuffered(self):
        """Test that Dockerfile sets PYTHONUNBUFFERED for proper logging."""
        self.assertIn(
            'PYTHONUNBUFFERED',
            self.dockerfile_content,
            "Dockerfile should set PYTHONUNBUFFERED for proper logging"
        )
    
    def test_dockerfile_sets_pythondontwritebytecode(self):
        """Test that Dockerfile prevents .pyc file generation."""
        self.assertIn(
            'PYTHONDONTWRITEBYTECODE',
            self.dockerfile_content,
            "Dockerfile should set PYTHONDONTWRITEBYTECODE"
        )
    
    def test_dockerfile_creates_git_directories(self):
        """Test that Dockerfile creates git checkout directories."""
        self.assertIn(
            'git_checkouts',
            self.dockerfile_content,
            "Dockerfile should create git checkout directories"
        )
    
    def test_dockerfile_uses_no_cache_for_pip(self):
        """Test that pip install uses --no-cache-dir for smaller image."""
        self.assertIn(
            '--no-cache-dir',
            self.dockerfile_content,
            "Dockerfile should use --no-cache-dir for smaller image size"
        )
    
    def test_dockerfile_cleans_apt_cache(self):
        """Test that Dockerfile cleans up apt cache."""
        self.assertIn(
            'rm -rf /var/lib/apt/lists/*',
            self.dockerfile_content,
            "Dockerfile should clean up apt cache for smaller image size"
        )


class DockerignoreTest(unittest.TestCase):
    """Tests for .dockerignore file."""
    
    @classmethod
    def setUpClass(cls):
        """Set up test fixtures."""
        cls.project_root = Path(__file__).resolve().parent.parent
        cls.dockerignore_path = cls.project_root / '.dockerignore'
        
        if cls.dockerignore_path.exists():
            with open(cls.dockerignore_path, 'r') as f:
                cls.dockerignore_content = f.read()
        else:
            cls.dockerignore_content = None
    
    def test_dockerignore_exists(self):
        """Test that .dockerignore exists in project root."""
        self.assertTrue(
            self.dockerignore_path.exists(),
            ".dockerignore should exist in project root"
        )
    
    def test_dockerignore_not_empty(self):
        """Test that .dockerignore is not empty."""
        self.assertIsNotNone(self.dockerignore_content, ".dockerignore should exist")
        self.assertGreater(
            len(self.dockerignore_content.strip()),
            0,
            ".dockerignore should not be empty"
        )
    
    def test_dockerignore_excludes_git(self):
        """Test that .dockerignore excludes .git directory."""
        self.assertIn(
            '.git',
            self.dockerignore_content,
            ".dockerignore should exclude .git directory"
        )
    
    def test_dockerignore_excludes_pycache(self):
        """Test that .dockerignore excludes __pycache__."""
        self.assertIn(
            '__pycache__',
            self.dockerignore_content,
            ".dockerignore should exclude __pycache__ directories"
        )
    
    def test_dockerignore_excludes_venv(self):
        """Test that .dockerignore excludes virtual environment directories."""
        content_lower = self.dockerignore_content.lower()
        self.assertTrue(
            'venv' in content_lower or '.venv' in content_lower,
            ".dockerignore should exclude virtual environment directories"
        )
    
    def test_dockerignore_excludes_env_file(self):
        """Test that .dockerignore excludes .env file."""
        self.assertIn(
            '.env',
            self.dockerignore_content,
            ".dockerignore should exclude .env file"
        )
    
    def test_dockerignore_excludes_sqlite(self):
        """Test that .dockerignore excludes SQLite database."""
        self.assertIn(
            'db.sqlite3',
            self.dockerignore_content,
            ".dockerignore should exclude SQLite database file"
        )
    
    def test_dockerignore_excludes_tmp(self):
        """Test that .dockerignore excludes tmp directory."""
        self.assertIn(
            'tmp/',
            self.dockerignore_content,
            ".dockerignore should exclude tmp directory"
        )
    
    def test_dockerignore_excludes_pyc_files(self):
        """Test that .dockerignore excludes .pyc files."""
        self.assertTrue(
            '*.py[cod]' in self.dockerignore_content or '*.pyc' in self.dockerignore_content,
            ".dockerignore should exclude .pyc files"
        )
    
    def test_dockerignore_excludes_ide_files(self):
        """Test that .dockerignore excludes IDE configuration files."""
        content = self.dockerignore_content
        # Check for common IDE directories
        self.assertTrue(
            '.idea/' in content or '.vscode/' in content,
            ".dockerignore should exclude IDE configuration directories"
        )


class DockerBuildSyntaxTest(unittest.TestCase):
    """Tests for Dockerfile syntax validation using Docker CLI (if available)."""
    
    @classmethod
    def setUpClass(cls):
        """Set up test fixtures."""
        cls.project_root = Path(__file__).resolve().parent.parent
        cls.dockerfile_path = cls.project_root / 'Dockerfile'
        
        # Check if Docker is available
        import subprocess
        try:
            result = subprocess.run(
                ['docker', '--version'],
                capture_output=True,
                text=True,
                timeout=10
            )
            cls.docker_available = result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            cls.docker_available = False
    
    def test_dockerfile_syntax_is_valid(self):
        """Test that Dockerfile syntax is valid using Docker's BuildKit check mode."""
        import subprocess
        
        if not self.docker_available:
            self.skipTest("Docker CLI not available")
        
        result = subprocess.run(
            ['docker', 'build', '--check', '-f', str(self.dockerfile_path), str(self.project_root)],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        self.assertEqual(
            result.returncode, 0,
            f"Dockerfile syntax check failed: {result.stderr}"
        )


if __name__ == '__main__':
    unittest.main()
