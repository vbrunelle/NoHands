# NoHands

A Django-based web interface for triggering Dagger pipelines to build and deploy Docker images from Git repositories.

## Features

- **Repository Management**: Browse Git repositories, branches, and commits
- **Build Pipeline**: Trigger Dagger-powered Docker image builds from any commit
- **Build History**: Track build status, logs, and image tags
- **REST API**: Full API access for automation and integration
- **Admin Interface**: Django admin for easy management

## Architecture

### Django Apps

- **projects**: Manages Git repositories, branches, and commits
- **builds**: Handles build requests, execution, and history
- **api**: REST API endpoints using Django REST Framework

### Key Components

- **Git Utilities** (`projects/git_utils.py`): GitPython-based functions for repository operations
- **Dagger Pipeline** (`builds/dagger_pipeline.py`): Async Docker image building with Dagger SDK
- **Django Models**: GitRepository, Branch, Commit, Build
- **REST API**: Full CRUD and build triggering via API

## Requirements

- Python 3.11+
- Django 5+
- Dagger (installed via Python SDK)
- Git
- Docker (for Dagger builds)

## Installation

1. **Clone the repository**:
```bash
git clone https://github.com/vbrunelle/NoHands.git
cd NoHands
```

2. **Install dependencies**:
```bash
pip install -r requirements.txt
```

3. **Run migrations**:
```bash
python manage.py migrate
```

4. **Create superuser** (for admin access):
```bash
python manage.py createsuperuser
```

5. **Run the development server**:
```bash
python manage.py runserver
```

6. **Access the application**:
- Web UI: http://localhost:8000/
- Admin: http://localhost:8000/admin/
- API: http://localhost:8000/api/

## Configuration

### Environment Variables

You can configure the following via environment variables:

```bash
# Docker Registry Settings
export DOCKER_REGISTRY="registry.example.com"
export DOCKER_REGISTRY_USERNAME="your-username"
export DOCKER_REGISTRY_PASSWORD="your-password"

# Concurrent builds limit
export MAX_CONCURRENT_BUILDS=1
```

### Settings

Key settings in `nohands_project/settings.py`:

- `GIT_CHECKOUT_DIR`: Directory for temporary Git checkouts
- `DOCKER_REGISTRY`: Docker registry URL
- `MAX_CONCURRENT_BUILDS`: Maximum concurrent build jobs

## Usage

### Web Interface

1. **Add a Repository**:
   - Go to Admin panel (http://localhost:8000/admin/)
   - Add a new Git Repository with URL and configuration
   - Example: `https://github.com/user/repo.git` or local path

2. **Browse Branches**:
   - View repository details
   - Click "Refresh Branches" to fetch from Git
   - Select a branch to view commits

3. **Trigger a Build**:
   - Navigate to a branch's commits
   - Click "🚀 Build" next to any commit
   - Configure build options (push to registry, etc.)
   - Start the build

4. **Monitor Builds**:
   - View all builds at `/builds/`
   - Click a build to see detailed logs
   - Builds run asynchronously in background threads

### REST API

#### List Repositories
```bash
curl http://localhost:8000/api/repositories/
```

#### List Branches
```bash
curl http://localhost:8000/api/branches/?repository=1
```

#### List Commits
```bash
curl http://localhost:8000/api/commits/?branch=1
```

#### List Builds
```bash
curl http://localhost:8000/api/builds/
```

#### Trigger a Build
```bash
curl -X POST http://localhost:8000/api/builds/trigger/ \
  -H "Content-Type: application/json" \
  -d '{
    "repository_id": 1,
    "commit_id": 1,
    "push_to_registry": false,
    "deploy_after_build": false
  }'
```

#### Get Build Details
```bash
curl http://localhost:8000/api/builds/1/
```

## Git Operations

The system uses GitPython for Git operations:

- **Clone/Update**: Repositories are cached locally for performance
- **Branch Listing**: Fetches all branches from repository
- **Commit History**: Lists commits with metadata
- **Checkout**: Creates isolated checkouts for builds

## Dagger Pipeline

The Dagger pipeline (`builds/dagger_pipeline.py`):

1. **Build Phase**:
   - Loads source directory
   - Builds Docker image using Dockerfile
   - Tags with commit SHA

2. **Push Phase** (optional):
   - Authenticates with registry
   - Pushes image with full tag
   - Returns image reference

3. **Output**:
   - Status (success/failed)
   - Build logs
   - Image tag
   - Duration

## Project Structure

```
NoHands/
├── manage.py
├── requirements.txt
├── Dockerfile.example
├── nohands_project/          # Django project settings
│   ├── settings.py
│   ├── urls.py
│   └── ...
├── projects/                 # Repository management app
│   ├── models.py             # GitRepository, Branch, Commit models
│   ├── views.py              # Web views
│   ├── admin.py              # Admin configuration
│   ├── git_utils.py          # Git utilities
│   ├── urls.py
│   └── templates/
│       └── projects/
├── builds/                   # Build management app
│   ├── models.py             # Build model
│   ├── views.py              # Build views
│   ├── admin.py
│   ├── dagger_pipeline.py    # Dagger build pipeline
│   ├── urls.py
│   └── templates/
│       └── builds/
└── api/                      # REST API app
    ├── views.py              # API viewsets
    ├── serializers.py        # DRF serializers
    └── urls.py
```

## Best Practices

### Security

- Never commit sensitive credentials to Git
- Use environment variables for registry credentials and SECRET_KEY
- Set `DJANGO_SECRET_KEY` environment variable in production
- Set `DJANGO_DEBUG=False` in production
- Set `DJANGO_ALLOWED_HOSTS` to your domain(s) in production
- Protect admin panel with strong passwords
- Use HTTPS in production
- Implement rate limiting for API endpoints

### Performance

- Repositories are cached to avoid repeated clones
- Builds run in background threads (for production, consider using Celery)
- Consider using Celery or Django-Q for production workloads
- Clean up old build directories periodically

### Production Deployment

**Important**: The current implementation uses background threads for build execution. For production deployments, consider:

1. **Task Queue**: Use Celery, Django-Q, or similar for reliable background job processing
2. **Message Broker**: Redis or RabbitMQ for task queue
3. **Process Manager**: Gunicorn or uWSGI instead of Django dev server
4. **Database**: PostgreSQL instead of SQLite
5. **Static Files**: Configure static file serving with WhiteNoise or CDN
6. **Monitoring**: Add logging, error tracking (Sentry), and monitoring

Example production environment variables:
```bash
export DJANGO_SECRET_KEY="your-long-random-secret-key-here"
export DJANGO_DEBUG=False
export DJANGO_ALLOWED_HOSTS="yourdomain.com,www.yourdomain.com"
export DOCKER_REGISTRY="registry.example.com"
export DOCKER_REGISTRY_USERNAME="your-username"
export DOCKER_REGISTRY_PASSWORD="your-password"
```

### Development

- Use Django's `check` command: `python manage.py check`
- Run tests: `python manage.py test`
- Use migrations for database changes
- Follow Django best practices

## Example Dockerfile

If your project doesn't have a Dockerfile, use `Dockerfile.example` as a template:

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
```

## Troubleshooting

### Build Fails with Git Error
- Ensure the repository URL is accessible
- Check Git credentials if using private repos
- Verify Git is installed: `git --version`

### Dagger Connection Failed
- Ensure Docker is running
- Check Dagger installation: `dagger version`
- Review Dagger logs in build output

### Registry Push Failed
- Verify registry credentials
- Ensure registry URL is correct
- Check network connectivity

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

This project is open source and available under the MIT License.

## Support

For issues and questions:
- GitHub Issues: https://github.com/vbrunelle/NoHands/issues
- Documentation: See this README

## Roadmap

- [ ] WebSocket support for real-time logs
- [ ] Celery integration for background tasks
- [ ] Kubernetes deployment support
- [ ] Multi-registry support
- [ ] Build notifications (email, Slack)
- [ ] Advanced build configurations
- [ ] Build artifacts management
- [ ] Build queue management