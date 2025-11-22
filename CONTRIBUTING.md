# Contributing to NoHands

First off, thank you for considering contributing to NoHands! It's people like you that make NoHands such a great tool. 🎉

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [How Can I Contribute?](#how-can-i-contribute)
- [Development Setup](#development-setup)
- [Development Workflow](#development-workflow)
- [Coding Standards](#coding-standards)
- [Testing Guidelines](#testing-guidelines)
- [Documentation Guidelines](#documentation-guidelines)
- [Pull Request Process](#pull-request-process)
- [Community](#community)

## Code of Conduct

This project and everyone participating in it is governed by our commitment to creating a welcoming and inclusive environment. By participating, you are expected to uphold this code:

- Be respectful and inclusive
- Be collaborative
- Be patient and welcoming
- Gracefully accept constructive criticism
- Focus on what is best for the community
- Show empathy towards other community members

## How Can I Contribute?

### Reporting Bugs

Before creating bug reports, please check the existing issues to avoid duplicates. When you create a bug report, include as many details as possible:

**Bug Report Template:**

```markdown
**Describe the bug**
A clear and concise description of what the bug is.

**To Reproduce**
Steps to reproduce the behavior:
1. Go to '...'
2. Click on '....'
3. Scroll down to '....'
4. See error

**Expected behavior**
A clear and concise description of what you expected to happen.

**Screenshots**
If applicable, add screenshots to help explain your problem.

**Environment:**
 - OS: [e.g. Ubuntu 22.04]
 - Python Version: [e.g. 3.11.5]
 - Django Version: [e.g. 5.0.1]
 - Docker Version: [e.g. 24.0.5]

**Additional context**
Add any other context about the problem here.
```

### Suggesting Features

Feature suggestions are welcome! Before creating a feature request, please check if it's already been suggested. When creating a feature request, include:

**Feature Request Template:**

```markdown
**Is your feature request related to a problem? Please describe.**
A clear and concise description of what the problem is.

**Describe the solution you'd like**
A clear and concise description of what you want to happen.

**Describe alternatives you've considered**
A clear and concise description of any alternative solutions or features you've considered.

**Use cases**
Describe specific use cases where this feature would be valuable.

**Additional context**
Add any other context or screenshots about the feature request here.
```

### Contributing Code

We love code contributions! Here are the types of contributions we're looking for:

- **Bug fixes**: Fix issues found in the issue tracker
- **New features**: Implement features from the roadmap or your own ideas
- **Documentation**: Improve or add to the documentation
- **Tests**: Add test coverage for existing or new features
- **Refactoring**: Improve code quality without changing functionality
- **Performance**: Optimize existing code

## Development Setup

### 1. Fork and Clone

```bash
# Fork the repository on GitHub, then clone your fork
git clone https://github.com/your-username/NoHands.git
cd NoHands

# Add upstream remote
git remote add upstream https://github.com/vbrunelle/NoHands.git
```

### 2. Set Up Development Environment

```bash
# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install development tools
pip install black flake8 isort pytest pytest-django pytest-cov mypy pylint
```

### 3. Configure Development Database

```bash
# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Load sample data (optional)
python manage.py loaddata sample_data.json  # If available
```

### 4. Verify Setup

```bash
# Run Django checks
python manage.py check

# Run tests
python manage.py test

# Start development server
python manage.py runserver
```

Visit http://localhost:8000 to verify everything works.

## Development Workflow

### 1. Create a Branch

Always create a new branch for your work:

```bash
# Update your local main
git checkout main
git pull upstream main

# Create a feature branch
git checkout -b feature/your-feature-name
# or for bug fixes
git checkout -b fix/bug-description
```

**Branch Naming Conventions:**
- `feature/` - New features
- `fix/` - Bug fixes
- `docs/` - Documentation changes
- `refactor/` - Code refactoring
- `test/` - Test additions or changes
- `chore/` - Maintenance tasks

### 2. Make Your Changes

- Write clean, readable code
- Follow the coding standards (see below)
- Add or update tests as needed
- Update documentation if needed
- Keep commits focused and atomic

### 3. Test Your Changes

```bash
# Run all tests
python manage.py test

# Run specific tests
python manage.py test projects.tests.TestGitUtils

# Run with coverage
coverage run --source='.' manage.py test
coverage report
coverage html  # Open htmlcov/index.html in browser

# Run linters
black .
flake8 .
isort .
mypy .
```

### 4. Commit Your Changes

Write clear, descriptive commit messages:

```bash
git add .
git commit -m "Add feature: short description

Longer description if needed. Explain what and why, not how.
The how is in the code.

Fixes #123"
```

**Commit Message Guidelines:**
- Use present tense ("Add feature" not "Added feature")
- Use imperative mood ("Move cursor to..." not "Moves cursor to...")
- First line max 50 characters
- Reference issues and PRs when relevant
- Add body if needed (after blank line)

**Good commit messages:**
```
Add Docker registry authentication support

Implement registry login before pushing images to support
private registries. Includes error handling and credential
validation.

Fixes #45
```

```
Fix: Handle git clone timeout errors

Add timeout handling for git operations to prevent hanging
when remote repositories are slow or unreachable.

Closes #67
```

### 5. Push and Create Pull Request

```bash
# Push your branch
git push origin feature/your-feature-name

# Create PR on GitHub
# Follow the PR template
```

## Coding Standards

### Python Style Guide

We follow [PEP 8](https://pep8.org/) with some modifications:

- **Line length**: 100 characters (not 79)
- **Indentation**: 4 spaces
- **Imports**: Use `isort` for consistent import ordering
- **Formatting**: Use `black` for automatic formatting

### Code Formatting Tools

```bash
# Format code with black
black .

# Sort imports with isort
isort .

# Check for style issues
flake8 .

# Type checking
mypy .
```

### Configuration Files

**pyproject.toml:**
```toml
[tool.black]
line-length = 100
target-version = ['py311']
exclude = '''
/(
    \.git
  | \.venv
  | venv
  | migrations
)/
'''

[tool.isort]
profile = "black"
line_length = 100
skip_gitignore = true

[tool.mypy]
python_version = "3.11"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = false
exclude = ["migrations", "venv"]
```

**.flake8:**
```ini
[flake8]
max-line-length = 100
exclude = 
    .git,
    __pycache__,
    */migrations/*,
    venv,
    .venv
ignore = E203, W503
```

### Django Best Practices

- **Models**: Use descriptive field names and add `help_text`
- **Views**: Keep views thin, move logic to models or utilities
- **Templates**: Use Django template inheritance
- **URLs**: Use meaningful URL names
- **Settings**: Never commit secrets, use environment variables
- **Migrations**: Always review migrations before committing

### Type Hints

Use type hints for function signatures:

```python
from typing import List, Dict, Optional
from pathlib import Path

def clone_or_update_repo(repo_url: str, local_path: Path) -> Repo:
    """
    Clone a repository or update it if it already exists.
    
    Args:
        repo_url: Git repository URL or local path
        local_path: Local path to clone/update the repository
        
    Returns:
        Repo: GitPython Repo object
        
    Raises:
        GitUtilsError: If cloning or updating fails
    """
    # Implementation
```

### Documentation Strings

Use Google-style docstrings:

```python
def example_function(param1: str, param2: int) -> bool:
    """
    Brief description of function.
    
    More detailed description if needed. Explain what the function
    does, not how it does it (that's what the code is for).
    
    Args:
        param1: Description of param1
        param2: Description of param2
        
    Returns:
        Description of return value
        
    Raises:
        ValueError: When param2 is negative
        TypeError: When param1 is not a string
        
    Example:
        >>> result = example_function("test", 42)
        >>> print(result)
        True
    """
    # Implementation
```

## Testing Guidelines

### Test Structure

Tests should be organized by app:

```
projects/
├── tests/
│   ├── __init__.py
│   ├── test_models.py
│   ├── test_views.py
│   ├── test_git_utils.py
│   └── test_api.py
```

### Writing Tests

```python
from django.test import TestCase
from projects.models import GitRepository

class GitRepositoryTestCase(TestCase):
    """Test cases for GitRepository model."""
    
    def setUp(self):
        """Set up test data."""
        self.repo = GitRepository.objects.create(
            name="test-repo",
            url="https://github.com/test/repo.git",
            description="Test repository",
            default_branch="main"
        )
    
    def test_repository_creation(self):
        """Test that repository is created correctly."""
        self.assertEqual(self.repo.name, "test-repo")
        self.assertTrue(self.repo.is_active)
    
    def test_repository_str(self):
        """Test string representation."""
        self.assertEqual(str(self.repo), "test-repo")
```

### Test Coverage

Aim for 80%+ test coverage:

```bash
# Run with coverage
coverage run --source='.' manage.py test
coverage report

# View detailed HTML report
coverage html
open htmlcov/index.html
```

### Testing Best Practices

- **Test one thing**: Each test should test a single behavior
- **Descriptive names**: Test names should describe what they test
- **Arrange-Act-Assert**: Structure tests clearly
- **Use fixtures**: Share common setup with fixtures
- **Mock external services**: Don't make real API calls or network requests
- **Test edge cases**: Test boundary conditions and error cases

## Documentation Guidelines

### Code Documentation

- **Functions**: Document all public functions
- **Classes**: Document all classes with their purpose
- **Modules**: Add module-level docstrings
- **Complex logic**: Comment complex algorithms or business logic

### README Updates

When adding features, update README.md with:
- Installation requirements (if new dependencies)
- Configuration options (if new settings)
- Usage examples (if new functionality)
- API documentation (if new endpoints)

### Changelog

Update CHANGELOG.md with:
- Features added
- Bugs fixed
- Breaking changes
- Deprecations

Format:
```markdown
## [Unreleased]

### Added
- New feature description (#PR_NUMBER)

### Fixed
- Bug fix description (#PR_NUMBER)

### Changed
- Changed feature description (#PR_NUMBER)
```

## Pull Request Process

### Before Creating a PR

1. **Update from upstream:**
   ```bash
   git checkout main
   git pull upstream main
   git checkout your-branch
   git rebase main
   ```

2. **Run all checks:**
   ```bash
   python manage.py test
   python manage.py check
   black .
   flake8 .
   isort .
   ```

3. **Update documentation:**
   - Update README if needed
   - Add docstrings to new functions
   - Update CHANGELOG.md

### Creating the PR

1. **Push your branch:**
   ```bash
   git push origin your-branch
   ```

2. **Create PR on GitHub** with:
   - Descriptive title
   - Detailed description
   - Screenshots/examples if applicable
   - Reference related issues

**PR Template:**
```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## How Has This Been Tested?
Describe tests that verify your changes

## Checklist
- [ ] My code follows the style guidelines
- [ ] I have performed a self-review
- [ ] I have commented my code where needed
- [ ] I have updated the documentation
- [ ] My changes generate no new warnings
- [ ] I have added tests that prove my fix/feature works
- [ ] New and existing unit tests pass locally
- [ ] Any dependent changes have been merged
```

### PR Review Process

1. **Automated checks** will run (tests, linting)
2. **Maintainer review** - expect feedback or approval
3. **Address feedback** - make requested changes
4. **Final approval** - PR will be merged
5. **Celebration** 🎉 - Your contribution is live!

### After PR is Merged

1. **Delete your branch:**
   ```bash
   git checkout main
   git pull upstream main
   git branch -d your-branch
   git push origin --delete your-branch
   ```

2. **Update your fork:**
   ```bash
   git push origin main
   ```

## Community

### Communication Channels

- **GitHub Issues**: Bug reports and feature requests
- **GitHub Discussions**: Questions and general discussion
- **Pull Requests**: Code contributions and reviews

### Getting Help

- Check existing documentation
- Search existing issues
- Ask in GitHub Discussions
- Create a new issue if needed

### Recognition

Contributors are recognized in:
- CHANGELOG.md
- GitHub contributors page
- Release notes
- Special thanks in major releases

## Questions?

Don't hesitate to ask! We're here to help:
- Open an issue with the "question" label
- Start a discussion on GitHub Discussions
- Reach out to maintainers

Thank you for contributing to NoHands! 🚀
