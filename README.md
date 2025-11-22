# NoHands

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![Django](https://img.shields.io/badge/django-5.0%2B-green)

**NoHands** is a powerful Django-based web interface for automating Docker image builds and deployments from Git repositories. It leverages [Dagger](https://dagger.io/) for reproducible builds and provides both a user-friendly web interface and a comprehensive REST API for complete automation.

## 🚀 Features

- **Repository Management**: Browse Git repositories, branches, and commits with automatic synchronization
- **Build Pipeline**: Trigger Dagger-powered Docker image builds from any commit with one click
- **Build History**: Track build status, logs, and image tags with detailed execution history
- **REST API**: Full REST API access for automation and CI/CD integration
- **Admin Interface**: Django admin for easy configuration and management
- **Real-time Logs**: View build logs and status updates in real-time
- **Registry Integration**: Push built images directly to Docker registries
- **Multi-branch Support**: Build from any branch or commit in your repository

## 📋 Table of Contents

- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [Usage Examples](#usage-examples)
  - [Web Interface Workflows](#web-interface-workflows)
  - [REST API Examples](#rest-api-examples)
- [Advanced Use Cases](#advanced-use-cases)
- [Production Deployment](#production-deployment)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)

## 🏗️ Architecture

NoHands is built on Django 5+ and uses a modular architecture with three main applications:

### Django Apps

- **projects**: Manages Git repositories, branches, and commits
  - Repository cloning and caching
  - Branch and commit synchronization
  - Git operations via GitPython
  
- **builds**: Handles build requests, execution, and history
  - Build queue management
  - Dagger pipeline execution
  - Build logs and status tracking
  
- **api**: REST API endpoints using Django REST Framework
  - Full CRUD operations
  - Build triggering and monitoring
  - API authentication and permissions

### Key Components

- **Git Utilities** (`projects/git_utils.py`): GitPython-based functions for repository operations
  - Clone or update repositories
  - List branches and commits
  - Checkout specific commits
  - Repository information retrieval

- **Dagger Pipeline** (`builds/dagger_pipeline.py`): Async Docker image building with Dagger SDK
  - Container building from Dockerfile
  - Registry authentication and push
  - Build result handling
  - Error management

- **Django Models**: 
  - `GitRepository`: Repository configuration and metadata
  - `Branch`: Branch tracking and latest commit info
  - `Commit`: Commit details (SHA, message, author, timestamp)
  - `Build`: Build requests, status, logs, and results

- **REST API**: Full CRUD and build triggering via API with pagination and filtering

## ✅ Prerequisites

Before installing NoHands, ensure you have the following installed:

### Required Software

- **Python 3.11 or higher**
  ```bash
  python --version  # Should show Python 3.11.x or higher
  ```

- **Git**
  ```bash
  git --version  # Should show git version 2.x or higher
  ```

- **Docker** (for Dagger builds)
  ```bash
  docker --version  # Should show Docker version 20.x or higher
  docker ps        # Should connect without errors
  ```

- **Dagger** (installed via Python SDK during pip install)
  - Dagger will be automatically installed with the Python dependencies
  - Requires Docker to be running

### System Requirements

- **Operating System**: Linux, macOS, or Windows (with WSL2)
- **RAM**: Minimum 2GB, recommended 4GB+ for building large projects
- **Disk Space**: Minimum 5GB for application and Docker images
- **Network**: Internet connection for cloning repositories and pulling Docker images

### Optional but Recommended

- **Virtual Environment**: Use `venv` or `virtualenv` to isolate dependencies
- **PostgreSQL**: For production deployments (SQLite is used by default for development)
- **Redis**: For task queues in production (if using Celery)

## Requirements

- Python 3.11+
- Django 5+
- Dagger (installed via Python SDK)
- Git
- Docker (for Dagger builds)

## 📦 Installation

### Step 1: Clone the Repository

```bash
git clone https://github.com/vbrunelle/NoHands.git
cd NoHands
```

### Step 2: Create a Virtual Environment (Recommended)

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Linux/macOS:
source venv/bin/activate
# On Windows:
venv\Scripts\activate
```

### Step 3: Install Python Dependencies

```bash
pip install -r requirements.txt
```

This will install:
- Django 5.0+
- Django REST Framework
- Dagger SDK (for Docker builds)
- GitPython (for Git operations)
- And other required dependencies

### Step 4: Set Up Environment Variables (Optional)

Create a `.env` file in the project root for environment-specific configuration:

```bash
# .env file
DJANGO_SECRET_KEY=your-secret-key-here
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1

# Docker Registry (optional)
DOCKER_REGISTRY=registry.example.com
DOCKER_REGISTRY_USERNAME=your-username
DOCKER_REGISTRY_PASSWORD=your-password

# Build Configuration
MAX_CONCURRENT_BUILDS=2
```

### Step 5: Run Database Migrations

```bash
python manage.py migrate
```

This creates the SQLite database and all necessary tables.

### Step 6: Create a Superuser Account

```bash
python manage.py createsuperuser
```

Follow the prompts to create an admin account:
- Username: (e.g., admin)
- Email: your-email@example.com
- Password: (enter a secure password)

### Step 7: Start the Development Server

```bash
python manage.py runserver
```

The server will start at `http://localhost:8000/`

### Step 8: Verify Installation

Open your browser and navigate to:
- **Web Interface**: http://localhost:8000/
- **Admin Panel**: http://localhost:8000/admin/
- **API Root**: http://localhost:8000/api/

Log in with the superuser credentials you created.

## 🎯 Quick Start

Let's walk through building your first Docker image with NoHands!

### 1. Add Your First Repository

1. Go to the Admin Panel: http://localhost:8000/admin/
2. Click on **Git Repositories** → **Add Git Repository**
3. Fill in the form:
   - **Name**: `my-project`
   - **URL**: `https://github.com/username/my-project.git` or a local path like `/path/to/repo`
   - **Description**: `My first project`
   - **Default Branch**: `main` (or `master`)
   - **Dockerfile Path**: `Dockerfile` (path to Dockerfile in your repo)
   - **Is Active**: ✅ checked
4. Click **Save**

### 2. Refresh Branches

1. Go to the main page: http://localhost:8000/
2. Click on your repository name
3. Click **Refresh Branches** button
4. Wait for branches to be fetched from Git

### 3. View Commits

1. Click on any branch name (e.g., `main`)
2. Click **Refresh Commits** to fetch latest commits
3. You'll see a list of commits with their messages, authors, and timestamps

### 4. Trigger a Build

1. In the commits list, click the **🚀 Build** button next to any commit
2. Configure build options:
   - **Push to Registry**: Check if you want to push to a Docker registry (requires registry configuration)
   - Leave unchecked for local builds
3. Click **Start Build**

### 5. Monitor the Build

1. You'll be redirected to the build detail page
2. The status will change from `pending` → `running` → `success` or `failed`
3. View real-time logs as the build progresses
4. Check the build duration and image tag when complete

That's it! You've successfully built your first Docker image with NoHands.

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

## ⚙️ Configuration

### Environment Variables

NoHands can be configured using environment variables. Create a `.env` file or set them in your shell:

#### Django Configuration

```bash
# Secret key for cryptographic signing (REQUIRED in production)
DJANGO_SECRET_KEY="your-long-random-secret-key-minimum-50-characters"

# Debug mode (set to False in production)
DJANGO_DEBUG=False

# Allowed hosts (comma-separated, required when DEBUG=False)
DJANGO_ALLOWED_HOSTS="example.com,www.example.com,localhost"
```

#### Docker Registry Settings

Configure these to enable pushing images to a Docker registry:

```bash
# Docker registry URL (without protocol)
DOCKER_REGISTRY="registry.example.com"
# Or for Docker Hub:
DOCKER_REGISTRY="docker.io"

# Registry authentication
DOCKER_REGISTRY_USERNAME="your-username"
DOCKER_REGISTRY_PASSWORD="your-password-or-token"
```

#### Build Configuration

```bash
# Maximum concurrent builds (default: 1)
# Increase if you have sufficient resources
MAX_CONCURRENT_BUILDS=3
```

### Settings File Configuration

You can also modify `nohands_project/settings.py` directly:

#### Git Checkout Directory

```python
# Directory for temporary Git checkouts
GIT_CHECKOUT_DIR = BASE_DIR / 'tmp' / 'git_checkouts'
```

This directory will contain:
- `cache/`: Cached repository clones
- `builds/`: Temporary checkouts for each build

#### Database Configuration

**Development (default):**
```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}
```

**Production (PostgreSQL recommended):**
```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'nohands',
        'USER': 'nohands_user',
        'PASSWORD': 'secure_password',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}
```

#### REST Framework Settings

```python
REST_FRAMEWORK = {
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    
    # Add authentication (optional)
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.TokenAuthentication',
    ],
    
    # Add permissions (optional)
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
}
```

### Repository Configuration

Each Git repository can be configured with:

| Field | Description | Example |
|-------|-------------|---------|
| **name** | Unique repository identifier | `my-app` |
| **url** | Git URL or local path | `https://github.com/user/repo.git` or `/path/to/repo` |
| **description** | Human-readable description | `Production application` |
| **default_branch** | Default branch name | `main`, `master`, `develop` |
| **dockerfile_path** | Path to Dockerfile in repo | `Dockerfile`, `docker/Dockerfile`, `build/Dockerfile` |
| **is_active** | Whether repo is active | `True` or `False` |

### Dockerfile Requirements

Your repository must contain a valid Dockerfile. Here's a minimal example:

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
```

See `Dockerfile.example` in the repository for a complete template.

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

## 🎨 Usage Examples

### Web Interface Workflows

#### Workflow 1: Building from a Specific Commit

**Use Case**: You want to build a Docker image from a specific commit in your repository.

1. **Navigate to Repository**
   - Go to http://localhost:8000/
   - Click on your repository name

2. **Select Branch**
   - Click on the branch containing your commit (e.g., `main`)
   - If you don't see branches, click **Refresh Branches** first

3. **Find Your Commit**
   - Browse the commit list or click **Refresh Commits** to get the latest
   - Identify your commit by message, author, or timestamp

4. **Trigger Build**
   - Click the **🚀 Build** button next to the commit
   - Configure options:
     - ☐ **Push to Registry**: Leave unchecked for local builds
     - ☑ **Push to Registry**: Check to push to configured registry
   - Click **Start Build**

5. **Monitor Progress**
   - View build status in real-time
   - Check logs for detailed output
   - Note the image tag when complete (e.g., `my-app:a1b2c3d4`)

#### Workflow 2: Building and Pushing to Registry

**Use Case**: Build an image and push it to Docker Hub or a private registry.

1. **Configure Registry** (one-time setup)
   - Set environment variables:
     ```bash
     export DOCKER_REGISTRY="registry.example.com"
     export DOCKER_REGISTRY_USERNAME="myusername"
     export DOCKER_REGISTRY_PASSWORD="mytoken"
     ```
   - Restart the Django server

2. **Trigger Build with Push**
   - Follow steps from Workflow 1
   - When configuring the build, check **☑ Push to Registry**
   - Click **Start Build**

3. **Verify in Registry**
   - After successful build, the image will be pushed
   - Image tag format: `registry.example.com/my-app:a1b2c3d4`
   - Check your registry dashboard to verify

#### Workflow 3: Building from Multiple Branches

**Use Case**: You maintain multiple environments (dev, staging, prod) in different branches.

1. **Add Repository** (if not already added)
   - Admin → Git Repositories → Add
   - Configure as shown in Quick Start

2. **Refresh Branches**
   - Navigate to repository detail
   - Click **Refresh Branches**
   - All branches will be synced

3. **Build from Each Branch**
   - Click on `develop` branch → Refresh Commits → Build from latest
   - Click on `staging` branch → Refresh Commits → Build from latest
   - Click on `main` branch → Refresh Commits → Build from latest

4. **Track All Builds**
   - Go to http://localhost:8000/builds/
   - See all builds across all repositories and branches
   - Filter by status: pending, running, success, failed

#### Workflow 4: Monitoring Build History

**Use Case**: Review past builds and their results.

1. **View All Builds**
   - Navigate to http://localhost:8000/builds/
   - See a chronological list of all builds

2. **Filter Builds**
   - Builds are listed with:
     - Build ID
     - Repository name
     - Commit SHA
     - Branch name
     - Status (pending/running/success/failed)
     - Created timestamp

3. **View Build Details**
   - Click on any build ID
   - See complete information:
     - Full build logs
     - Error messages (if failed)
     - Image tag generated
     - Build duration
     - Configuration used

4. **Analyze Failures**
   - Check error messages in failed builds
   - Review logs to debug issues
   - Identify patterns in failures

### REST API Examples

The REST API enables full automation and integration with CI/CD pipelines.

#### Example 1: List All Repositories

**Request:**
```bash
curl http://localhost:8000/api/repositories/
```

**Response:**
```json
{
  "count": 2,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 1,
      "name": "my-app",
      "url": "https://github.com/user/my-app.git",
      "description": "My application",
      "default_branch": "main",
      "is_active": true,
      "created_at": "2025-01-15T10:00:00Z"
    },
    {
      "id": 2,
      "name": "another-app",
      "url": "https://github.com/user/another-app.git",
      "description": "Another application",
      "default_branch": "master",
      "is_active": true,
      "created_at": "2025-01-16T11:00:00Z"
    }
  ]
}
```

#### Example 2: Get Repository Details

**Request:**
```bash
curl http://localhost:8000/api/repositories/1/
```

**Response:**
```json
{
  "id": 1,
  "name": "my-app",
  "url": "https://github.com/user/my-app.git",
  "description": "My application",
  "default_branch": "main",
  "is_active": true,
  "created_at": "2025-01-15T10:00:00Z"
}
```

#### Example 3: List Branches for a Repository

**Request:**
```bash
curl "http://localhost:8000/api/branches/?repository=1"
```

**Response:**
```json
{
  "count": 3,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 1,
      "repository_name": "my-app",
      "name": "main",
      "commit_sha": "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0",
      "last_updated": "2025-01-15T12:00:00Z"
    },
    {
      "id": 2,
      "repository_name": "my-app",
      "name": "develop",
      "commit_sha": "b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1",
      "last_updated": "2025-01-15T12:00:00Z"
    },
    {
      "id": 3,
      "repository_name": "my-app",
      "name": "feature/new-ui",
      "commit_sha": "c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2",
      "last_updated": "2025-01-15T12:00:00Z"
    }
  ]
}
```

#### Example 4: List Commits for a Branch

**Request:**
```bash
curl "http://localhost:8000/api/commits/?branch=1"
```

**Response:**
```json
{
  "count": 50,
  "next": "http://localhost:8000/api/commits/?branch=1&page=2",
  "previous": null,
  "results": [
    {
      "id": 101,
      "repository_name": "my-app",
      "branch_name": "main",
      "sha": "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0",
      "message": "Add new feature",
      "author": "John Doe",
      "author_email": "john@example.com",
      "committed_at": "2025-01-15T14:30:00Z"
    },
    {
      "id": 100,
      "repository_name": "my-app",
      "branch_name": "main",
      "sha": "b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1",
      "message": "Fix bug in authentication",
      "author": "Jane Smith",
      "author_email": "jane@example.com",
      "committed_at": "2025-01-14T16:45:00Z"
    }
  ]
}
```

#### Example 5: Trigger a Build (Most Important!)

**Request:**
```bash
curl -X POST http://localhost:8000/api/builds/trigger/ \
  -H "Content-Type: application/json" \
  -d '{
    "repository_id": 1,
    "commit_id": 101,
    "push_to_registry": false,
    "deploy_after_build": false
  }'
```

**Response:**
```json
{
  "id": 42,
  "repository_name": "my-app",
  "commit_sha": "a1b2c3d4",
  "branch_name": "main",
  "status": "pending",
  "image_tag": "",
  "logs": "",
  "error_message": "",
  "created_at": "2025-01-15T15:00:00Z",
  "started_at": null,
  "completed_at": null,
  "push_to_registry": false,
  "duration": "N/A"
}
```

#### Example 6: Get Build Status

**Request:**
```bash
curl http://localhost:8000/api/builds/42/
```

**Response (Running):**
```json
{
  "id": 42,
  "repository_name": "my-app",
  "commit_sha": "a1b2c3d4",
  "branch_name": "main",
  "status": "running",
  "image_tag": "",
  "logs": "Starting build for my-app:a1b2c3d4\nBuilding image from Dockerfile\n...",
  "error_message": "",
  "created_at": "2025-01-15T15:00:00Z",
  "started_at": "2025-01-15T15:00:05Z",
  "completed_at": null,
  "push_to_registry": false,
  "duration": "N/A"
}
```

**Response (Success):**
```json
{
  "id": 42,
  "repository_name": "my-app",
  "commit_sha": "a1b2c3d4",
  "branch_name": "main",
  "status": "success",
  "image_tag": "my-app:a1b2c3d4",
  "logs": "Starting build for my-app:a1b2c3d4\nBuilding image from Dockerfile\n...\nBuild completed successfully in 125.45 seconds",
  "error_message": "",
  "created_at": "2025-01-15T15:00:00Z",
  "started_at": "2025-01-15T15:00:05Z",
  "completed_at": "2025-01-15T15:02:10Z",
  "push_to_registry": false,
  "duration": "2m 5s"
}
```

#### Example 7: List All Builds

**Request:**
```bash
curl http://localhost:8000/api/builds/
```

**With Filtering:**
```bash
# Filter by repository
curl "http://localhost:8000/api/builds/?repository=1"

# Filter by status
curl "http://localhost:8000/api/builds/?status=success"

# Combine filters
curl "http://localhost:8000/api/builds/?repository=1&status=failed"
```

#### Example 8: CI/CD Integration Script

Here's a complete script for CI/CD integration:

```bash
#!/bin/bash
# build_and_deploy.sh - Trigger NoHands build from CI/CD

NOHANDS_URL="http://localhost:8000"
REPOSITORY_ID=1
COMMIT_SHA="$CI_COMMIT_SHA"  # From your CI system

# 1. Find the commit ID
COMMIT_ID=$(curl -s "${NOHANDS_URL}/api/commits/?repository=${REPOSITORY_ID}" | \
  jq -r ".results[] | select(.sha==\"${COMMIT_SHA}\") | .id")

if [ -z "$COMMIT_ID" ]; then
  echo "Error: Commit not found"
  exit 1
fi

# 2. Trigger build
BUILD_RESPONSE=$(curl -s -X POST "${NOHANDS_URL}/api/builds/trigger/" \
  -H "Content-Type: application/json" \
  -d "{
    \"repository_id\": ${REPOSITORY_ID},
    \"commit_id\": ${COMMIT_ID},
    \"push_to_registry\": true,
    \"deploy_after_build\": false
  }")

BUILD_ID=$(echo "$BUILD_RESPONSE" | jq -r '.id')
echo "Build triggered: #${BUILD_ID}"

# 3. Poll for completion
while true; do
  BUILD_STATUS=$(curl -s "${NOHANDS_URL}/api/builds/${BUILD_ID}/" | jq -r '.status')
  
  echo "Build status: ${BUILD_STATUS}"
  
  if [ "$BUILD_STATUS" = "success" ]; then
    echo "Build completed successfully!"
    exit 0
  elif [ "$BUILD_STATUS" = "failed" ]; then
    echo "Build failed!"
    curl -s "${NOHANDS_URL}/api/builds/${BUILD_ID}/" | jq -r '.error_message'
    exit 1
  fi
  
  sleep 10
done
```

#### Example 9: Python Integration

```python
import requests
import time

class NoHandsClient:
    def __init__(self, base_url):
        self.base_url = base_url.rstrip('/')
    
    def trigger_build(self, repository_id, commit_id, push_to_registry=False):
        """Trigger a new build."""
        url = f"{self.base_url}/api/builds/trigger/"
        data = {
            "repository_id": repository_id,
            "commit_id": commit_id,
            "push_to_registry": push_to_registry,
            "deploy_after_build": False
        }
        response = requests.post(url, json=data)
        response.raise_for_status()
        return response.json()
    
    def get_build_status(self, build_id):
        """Get build status."""
        url = f"{self.base_url}/api/builds/{build_id}/"
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    
    def wait_for_build(self, build_id, timeout=3600, poll_interval=10):
        """Wait for build to complete."""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            build = self.get_build_status(build_id)
            status = build['status']
            
            print(f"Build {build_id}: {status}")
            
            if status == 'success':
                return build
            elif status == 'failed':
                raise Exception(f"Build failed: {build['error_message']}")
            
            time.sleep(poll_interval)
        
        raise TimeoutError(f"Build {build_id} timed out after {timeout}s")

# Usage
client = NoHandsClient("http://localhost:8000")

# Trigger build
build = client.trigger_build(repository_id=1, commit_id=101, push_to_registry=True)
print(f"Build triggered: #{build['id']}")

# Wait for completion
result = client.wait_for_build(build['id'])
print(f"Build completed: {result['image_tag']}")
```

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

## 🚀 Advanced Use Cases

### Use Case 1: Multi-Environment Deployment Pipeline

**Scenario**: You have three environments (dev, staging, production) with different branches.

**Setup:**

1. **Configure Repository with Multiple Branches**
   ```bash
   # Add repository via API or Admin
   # Branches: develop, staging, main
   ```

2. **Create Deployment Script**
   ```bash
   #!/bin/bash
   # deploy.sh
   
   ENVIRONMENT=$1  # dev, staging, or prod
   NOHANDS_URL="http://nohands.internal.company.com"
   
   case $ENVIRONMENT in
     dev)
       BRANCH="develop"
       REGISTRY="dev-registry.company.com"
       ;;
     staging)
       BRANCH="staging"
       REGISTRY="staging-registry.company.com"
       ;;
     prod)
       BRANCH="main"
       REGISTRY="prod-registry.company.com"
       ;;
     *)
       echo "Invalid environment"
       exit 1
       ;;
   esac
   
   # Get latest commit from branch
   COMMIT_ID=$(curl -s "${NOHANDS_URL}/api/commits/?branch=${BRANCH}&limit=1" | \
     jq -r '.results[0].id')
   
   # Trigger build
   curl -X POST "${NOHANDS_URL}/api/builds/trigger/" \
     -H "Content-Type: application/json" \
     -d "{
       \"repository_id\": 1,
       \"commit_id\": ${COMMIT_ID},
       \"push_to_registry\": true
     }"
   ```

3. **Use in CI/CD**
   ```yaml
   # .gitlab-ci.yml or similar
   deploy_dev:
     script: ./deploy.sh dev
     only:
       - develop
   
   deploy_staging:
     script: ./deploy.sh staging
     only:
       - staging
   
   deploy_prod:
     script: ./deploy.sh prod
     only:
       - main
     when: manual
   ```

### Use Case 2: Building Multiple Microservices

**Scenario**: You have a monorepo with multiple services, each with its own Dockerfile.

**Setup:**

1. **Add Multiple Repositories** (one per service)
   ```python
   # Via Django admin or API
   repositories = [
       {
           "name": "api-service",
           "url": "/path/to/monorepo",
           "dockerfile_path": "services/api/Dockerfile"
       },
       {
           "name": "worker-service",
           "url": "/path/to/monorepo",
           "dockerfile_path": "services/worker/Dockerfile"
       },
       {
           "name": "frontend-service",
           "url": "/path/to/monorepo",
           "dockerfile_path": "services/frontend/Dockerfile"
       }
   ]
   ```

2. **Build All Services Script**
   ```bash
   #!/bin/bash
   # build_all_services.sh
   
   SERVICES=("api-service" "worker-service" "frontend-service")
   COMMIT_SHA=$1
   
   for SERVICE in "${SERVICES[@]}"; do
     echo "Building ${SERVICE}..."
     
     # Get repository ID
     REPO_ID=$(curl -s "http://localhost:8000/api/repositories/" | \
       jq -r ".results[] | select(.name==\"${SERVICE}\") | .id")
     
     # Get commit ID
     COMMIT_ID=$(curl -s "http://localhost:8000/api/commits/?repository=${REPO_ID}" | \
       jq -r ".results[] | select(.sha==\"${COMMIT_SHA}\") | .id")
     
     # Trigger build
     BUILD_ID=$(curl -s -X POST "http://localhost:8000/api/builds/trigger/" \
       -H "Content-Type: application/json" \
       -d "{
         \"repository_id\": ${REPO_ID},
         \"commit_id\": ${COMMIT_ID},
         \"push_to_registry\": true
       }" | jq -r '.id')
     
     echo "Build triggered for ${SERVICE}: #${BUILD_ID}"
   done
   ```

### Use Case 3: Automated Rollback

**Scenario**: Automatically rollback to the previous working build if deployment fails.

**Implementation:**

```python
#!/usr/bin/env python3
# rollback.py

import requests
import sys

class DeploymentManager:
    def __init__(self, nohands_url):
        self.base_url = nohands_url.rstrip('/')
    
    def get_successful_builds(self, repository_id, limit=10):
        """Get recent successful builds."""
        url = f"{self.base_url}/api/builds/"
        params = {
            'repository': repository_id,
            'status': 'success',
            'ordering': '-completed_at'
        }
        response = requests.get(url, params=params)
        return response.json()['results'][:limit]
    
    def trigger_rollback(self, repository_id):
        """Rollback to previous successful build."""
        builds = self.get_successful_builds(repository_id, limit=2)
        
        if len(builds) < 2:
            print("Not enough successful builds for rollback")
            return None
        
        previous_build = builds[1]  # Second most recent
        commit_id = previous_build['commit_id']
        
        print(f"Rolling back to commit: {previous_build['commit_sha']}")
        
        # Trigger new build with previous commit
        url = f"{self.base_url}/api/builds/trigger/"
        data = {
            'repository_id': repository_id,
            'commit_id': commit_id,
            'push_to_registry': True
        }
        response = requests.post(url, json=data)
        return response.json()

# Usage
manager = DeploymentManager("http://localhost:8000")
rollback_build = manager.trigger_rollback(repository_id=1)
print(f"Rollback build triggered: #{rollback_build['id']}")
```

### Use Case 4: Build Status Notifications

**Scenario**: Send notifications when builds complete or fail.

**Implementation:**

```python
#!/usr/bin/env python3
# build_monitor.py

import requests
import time
import smtplib
from email.mime.text import MIMEText

class BuildMonitor:
    def __init__(self, nohands_url, smtp_config):
        self.base_url = nohands_url.rstrip('/')
        self.smtp_config = smtp_config
        self.seen_builds = set()
    
    def send_notification(self, build):
        """Send email notification."""
        subject = f"Build #{build['id']} {build['status']}: {build['repository_name']}"
        body = f"""
        Build Details:
        - Repository: {build['repository_name']}
        - Commit: {build['commit_sha']}
        - Branch: {build['branch_name']}
        - Status: {build['status']}
        - Duration: {build['duration']}
        
        Image Tag: {build['image_tag']}
        
        Error: {build['error_message']}
        
        View build: {self.base_url}/builds/{build['id']}/
        """
        
        msg = MIMEText(body)
        msg['Subject'] = subject
        msg['From'] = self.smtp_config['from']
        msg['To'] = self.smtp_config['to']
        
        with smtplib.SMTP(self.smtp_config['host'], self.smtp_config['port']) as server:
            server.send_message(msg)
    
    def monitor(self, interval=30):
        """Monitor builds and send notifications."""
        while True:
            # Get recent builds
            url = f"{self.base_url}/api/builds/"
            response = requests.get(url, params={'ordering': '-created_at'})
            builds = response.json()['results']
            
            for build in builds:
                build_id = build['id']
                status = build['status']
                
                # Check if build is complete and not seen
                if build_id not in self.seen_builds and status in ['success', 'failed']:
                    print(f"Build #{build_id} completed with status: {status}")
                    self.send_notification(build)
                    self.seen_builds.add(build_id)
            
            time.sleep(interval)

# Usage
smtp_config = {
    'host': 'smtp.example.com',
    'port': 587,
    'from': 'builds@example.com',
    'to': 'team@example.com'
}

monitor = BuildMonitor("http://localhost:8000", smtp_config)
monitor.monitor(interval=30)
```

### Use Case 5: Scheduled Nightly Builds

**Scenario**: Build the latest commit from main branch every night.

**Implementation using cron:**

```bash
# Add to crontab: crontab -e
# Run nightly build at 2 AM
0 2 * * * /usr/local/bin/nightly_build.sh >> /var/log/nightly_builds.log 2>&1
```

**nightly_build.sh:**
```bash
#!/bin/bash
# nightly_build.sh

NOHANDS_URL="http://localhost:8000"
REPOSITORY_ID=1

# Get latest commit from main branch
LATEST_COMMIT=$(curl -s "${NOHANDS_URL}/api/commits/?repository=${REPOSITORY_ID}&branch=main&limit=1" | \
  jq -r '.results[0]')

COMMIT_ID=$(echo "$LATEST_COMMIT" | jq -r '.id')
COMMIT_SHA=$(echo "$LATEST_COMMIT" | jq -r '.sha')

echo "[$(date)] Starting nightly build for commit ${COMMIT_SHA}"

# Trigger build
BUILD_RESPONSE=$(curl -s -X POST "${NOHANDS_URL}/api/builds/trigger/" \
  -H "Content-Type: application/json" \
  -d "{
    \"repository_id\": ${REPOSITORY_ID},
    \"commit_id\": ${COMMIT_ID},
    \"push_to_registry\": true
  }")

BUILD_ID=$(echo "$BUILD_RESPONSE" | jq -r '.id')
echo "[$(date)] Build triggered: #${BUILD_ID}"
```

### Use Case 6: Local Repository Builds

**Scenario**: Build from a local Git repository instead of remote.

**Setup:**

1. **Add Local Repository**
   ```python
   # Via Django admin
   Name: my-local-project
   URL: /home/user/projects/my-app
   Dockerfile Path: Dockerfile
   ```

2. **Build Process**
   - NoHands will use the local path directly
   - No cloning needed, faster builds
   - Useful for development and testing

3. **Update Local Repo**
   ```bash
   # Make changes
   cd /home/user/projects/my-app
   git commit -am "Update feature"
   
   # Refresh in NoHands
   curl -X POST "http://localhost:8000/refresh-branches/" # Via web UI
   
   # Trigger build
   # Use the web UI or API to build from the new commit
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

## 📁 Project Structure

```
NoHands/
├── manage.py                      # Django management script
├── requirements.txt               # Python dependencies
├── Dockerfile.example             # Example Dockerfile for projects
├── .gitignore                     # Git ignore rules
├── README.md                      # This file
│
├── nohands_project/              # Django project settings
│   ├── __init__.py
│   ├── settings.py               # Main settings file
│   ├── urls.py                   # Root URL configuration
│   ├── wsgi.py                   # WSGI application
│   └── asgi.py                   # ASGI application
│
├── projects/                     # Repository management app
│   ├── models.py                 # GitRepository, Branch, Commit models
│   ├── views.py                  # Web views for repositories
│   ├── admin.py                  # Admin configuration
│   ├── git_utils.py              # Git utilities (clone, list branches, etc.)
│   ├── urls.py                   # App URL patterns
│   ├── apps.py                   # App configuration
│   ├── tests.py                  # Unit tests
│   ├── migrations/               # Database migrations
│   └── templates/
│       ├── base.html             # Base template
│       └── projects/
│           ├── repository_list.html     # List repositories
│           ├── repository_detail.html   # Repository details
│           └── branch_commits.html      # Branch commits
│
├── builds/                       # Build management app
│   ├── models.py                 # Build model
│   ├── views.py                  # Build views and execution
│   ├── admin.py                  # Admin configuration
│   ├── dagger_pipeline.py        # Dagger build pipeline
│   ├── urls.py                   # App URL patterns
│   ├── apps.py                   # App configuration
│   ├── tests.py                  # Unit tests
│   ├── migrations/               # Database migrations
│   └── templates/
│       └── builds/
│           ├── build_list.html          # List builds
│           ├── build_detail.html        # Build details and logs
│           └── build_create.html        # Create build form
│
├── api/                          # REST API app
│   ├── views.py                  # API viewsets (repositories, builds, etc.)
│   ├── serializers.py            # DRF serializers
│   ├── urls.py                   # API URL patterns
│   ├── apps.py                   # App configuration
│   ├── admin.py                  # Admin configuration
│   ├── tests.py                  # API tests
│   └── migrations/               # Database migrations
│
└── tmp/                          # Temporary files (auto-created, gitignored)
    └── git_checkouts/
        ├── cache/                # Cached repository clones
        │   └── repo-name/       # One directory per repository
        └── builds/              # Temporary checkouts for builds
            └── build_123/       # One directory per build
```

### Key Files Explained

- **manage.py**: Django's command-line utility for administrative tasks
- **requirements.txt**: Lists all Python package dependencies
- **settings.py**: Django configuration (database, apps, middleware, etc.)
- **models.py**: Database models defining data structure
- **views.py**: Request handlers for web pages
- **serializers.py**: Data serialization for REST API
- **git_utils.py**: Reusable Git operations (clone, list branches, checkout)
- **dagger_pipeline.py**: Docker build logic using Dagger SDK
- **templates/**: HTML templates for web interface
- **migrations/**: Database schema changes tracked by Django

## 👥 Contributing

We welcome contributions to NoHands! Here's how you can help:

### Ways to Contribute

1. **Report Bugs**: Open an issue describing the bug and how to reproduce it
2. **Suggest Features**: Open an issue describing the feature and its use case
3. **Submit Pull Requests**: Fix bugs or implement features
4. **Improve Documentation**: Help make the docs better
5. **Write Tests**: Add test coverage for existing features

### Development Setup

1. **Fork and Clone:**
   ```bash
   git clone https://github.com/your-username/NoHands.git
   cd NoHands
   ```

2. **Create Virtual Environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # or venv\Scripts\activate on Windows
   ```

3. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Install Development Tools:**
   ```bash
   pip install black flake8 pytest pytest-django
   ```

5. **Run Migrations:**
   ```bash
   python manage.py migrate
   ```

6. **Create Superuser:**
   ```bash
   python manage.py createsuperuser
   ```

7. **Run Development Server:**
   ```bash
   python manage.py runserver
   ```

### Coding Standards

- **Python Style**: Follow PEP 8 guidelines
- **Formatting**: Use `black` for code formatting
  ```bash
  black .
  ```
- **Linting**: Use `flake8` for linting
  ```bash
  flake8 .
  ```
- **Type Hints**: Use type hints where appropriate
- **Docstrings**: Add docstrings to functions and classes
- **Comments**: Comment complex logic

### Running Tests

```bash
# Run all tests
python manage.py test

# Run specific app tests
python manage.py test projects
python manage.py test builds
python manage.py test api

# Run with coverage
pip install coverage
coverage run --source='.' manage.py test
coverage report
```

### Pull Request Process

1. **Create a Branch:**
   ```bash
   git checkout -b feature/your-feature-name
   # or
   git checkout -b fix/your-bug-fix
   ```

2. **Make Changes:**
   - Write code following the coding standards
   - Add tests for new features
   - Update documentation if needed

3. **Test Your Changes:**
   ```bash
   python manage.py test
   python manage.py check
   black .
   flake8 .
   ```

4. **Commit with Clear Messages:**
   ```bash
   git add .
   git commit -m "Add feature: description of feature"
   # or
   git commit -m "Fix: description of bug fix"
   ```

5. **Push to Your Fork:**
   ```bash
   git push origin feature/your-feature-name
   ```

6. **Open Pull Request:**
   - Go to GitHub and open a PR
   - Describe your changes clearly
   - Reference any related issues

### Commit Message Guidelines

- Use present tense ("Add feature" not "Added feature")
- Use imperative mood ("Move cursor to..." not "Moves cursor to...")
- First line should be concise (50 chars or less)
- Add detailed description after blank line if needed

Examples:
```
Add support for multi-stage Dockerfiles

Implement parsing of multi-stage Dockerfile syntax and
update build pipeline to handle multiple build stages.

Fixes #123
```

### Code Review Process

1. Maintainers will review your PR
2. Address any feedback or requested changes
3. Once approved, your PR will be merged
4. Your contribution will be credited in the release notes

### Development Tips

- **Use Django Shell for Testing:**
  ```bash
  python manage.py shell
  ```

- **Check Migrations:**
  ```bash
  python manage.py makemigrations --dry-run
  python manage.py makemigrations
  ```

- **Run Individual Tests:**
  ```bash
  python manage.py test projects.tests.TestGitUtils
  ```

- **Debug with IPython:**
  ```bash
  pip install ipython
  # Use in code: import IPython; IPython.embed()
  ```

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

## 🏭 Production Deployment

### Important Considerations

**⚠️ WARNING**: The current implementation uses background threads for build execution. For production deployments, you **MUST** use a proper task queue system like Celery or Django-Q for reliable background job processing.

### Production Checklist

Before deploying to production, ensure you've completed:

- [ ] Set `DJANGO_DEBUG=False`
- [ ] Set a strong `DJANGO_SECRET_KEY` (minimum 50 characters)
- [ ] Configure `DJANGO_ALLOWED_HOSTS` with your domain(s)
- [ ] Switch from SQLite to PostgreSQL
- [ ] Set up a task queue (Celery/Django-Q)
- [ ] Configure a message broker (Redis/RabbitMQ)
- [ ] Use a production WSGI server (Gunicorn/uWSGI)
- [ ] Set up static file serving (WhiteNoise/CDN)
- [ ] Configure Docker registry credentials securely
- [ ] Set up SSL/TLS (HTTPS)
- [ ] Configure log aggregation and monitoring
- [ ] Set up automated backups
- [ ] Implement rate limiting on API endpoints
- [ ] Configure firewall rules

### Quick Production Setup

For a complete production setup guide with Celery, Gunicorn, Nginx, PostgreSQL, and Docker Compose, see the **DEPLOYMENT.md** file (recommended for production environments).

### Minimal Production Configuration

If you need a quick production setup, here are the essential changes:

**1. Environment Variables:**
```bash
export DJANGO_SECRET_KEY="your-long-random-secret-key-minimum-50-characters"
export DJANGO_DEBUG=False
export DJANGO_ALLOWED_HOSTS="yourdomain.com,www.yourdomain.com"
export DOCKER_REGISTRY="registry.example.com"
export DOCKER_REGISTRY_USERNAME="your-username"
export DOCKER_REGISTRY_PASSWORD="your-password"
```

**2. Use PostgreSQL:**
```bash
# Install PostgreSQL
sudo apt-get install postgresql

# Create database
sudo -u postgres createdb nohands
sudo -u postgres createuser nohands_user

# Update settings
export DB_NAME=nohands
export DB_USER=nohands_user
export DB_PASSWORD=secure_password
```

**3. Use Gunicorn:**
```bash
pip install gunicorn
gunicorn nohands_project.wsgi:application --bind 0.0.0.0:8000 --workers 4
```

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

## 🔧 Troubleshooting

### Common Issues and Solutions

#### Issue 1: Build Fails with "Git Error"

**Symptoms:**
- Build status shows `failed`
- Error message contains Git-related errors

**Solutions:**
1. **Check Repository URL:**
   ```bash
   # Verify the URL is accessible
   git ls-remote <repository-url>
   ```

2. **For Private Repositories:**
   - Use SSH URL with proper SSH keys configured
   - Or use HTTPS with credentials: `https://username:token@github.com/user/repo.git`

3. **For Local Repositories:**
   - Ensure the path is absolute and accessible
   - Check file permissions

4. **Refresh Repository:**
   - Go to repository detail page
   - Click "Refresh Branches" to re-sync

#### Issue 2: "Dagger Connection Failed"

**Symptoms:**
- Build fails immediately
- Error mentions Dagger or Docker connection

**Solutions:**
1. **Ensure Docker is Running:**
   ```bash
   docker ps
   # Should list containers without errors
   ```

2. **Check Docker Socket Permissions:**
   ```bash
   sudo usermod -aG docker $USER
   # Log out and back in for changes to take effect
   ```

3. **Verify Dagger Installation:**
   ```bash
   python -c "import dagger; print(dagger.__version__)"
   ```

4. **Check Docker Version:**
   ```bash
   docker --version
   # Should be 20.x or higher
   ```

#### Issue 3: "Registry Push Failed"

**Symptoms:**
- Build succeeds but push fails
- Error mentions authentication or registry

**Solutions:**
1. **Verify Registry Credentials:**
   ```bash
   echo $DOCKER_REGISTRY_USERNAME
   echo $DOCKER_REGISTRY_PASSWORD  # (be careful not to expose)
   ```

2. **Test Registry Login Manually:**
   ```bash
   docker login $DOCKER_REGISTRY -u $DOCKER_REGISTRY_USERNAME -p $DOCKER_REGISTRY_PASSWORD
   ```

3. **Check Registry URL Format:**
   - Should NOT include `http://` or `https://`
   - Example: `registry.example.com` not `https://registry.example.com`

4. **Verify Network Connectivity:**
   ```bash
   ping registry.example.com
   curl -I https://registry.example.com
   ```

#### Issue 4: "Module Not Found" After Installation

**Symptoms:**
- Import errors when running Django commands
- Missing dependency errors

**Solutions:**
1. **Activate Virtual Environment:**
   ```bash
   source venv/bin/activate  # Linux/macOS
   venv\Scripts\activate      # Windows
   ```

2. **Reinstall Dependencies:**
   ```bash
   pip install -r requirements.txt --force-reinstall
   ```

3. **Check Python Version:**
   ```bash
   python --version  # Should be 3.11+
   ```

#### Issue 5: "Permission Denied" Errors

**Symptoms:**
- Cannot clone repositories
- Cannot create build directories
- Cannot write to database

**Solutions:**
1. **Check Directory Permissions:**
   ```bash
   ls -la /path/to/NoHands/tmp
   # Ensure current user has write permissions
   ```

2. **Create Directories with Correct Permissions:**
   ```bash
   mkdir -p tmp/git_checkouts/cache
   mkdir -p tmp/git_checkouts/builds
   chmod -R 755 tmp/
   ```

3. **For Database:**
   ```bash
   # SQLite
   chmod 664 db.sqlite3
   
   # PostgreSQL - check connection permissions
   sudo -u postgres psql -c "\du"
   ```

#### Issue 6: Builds Stuck in "Pending" Status

**Symptoms:**
- Builds never start
- Status remains "pending" indefinitely

**Solutions:**
1. **Check for Exceptions:**
   ```bash
   # View Django logs
   python manage.py runserver  # Check console output
   
   # Or check log files if configured
   tail -f /var/log/nohands/django.log
   ```

2. **Verify Threading/Celery:**
   - If using threads: Ensure no exceptions in the thread
   - If using Celery: Check Celery worker is running
     ```bash
     celery -A nohands_project inspect active
     ```

3. **Check Database Locks:**
   ```bash
   # For SQLite, check if file is locked
   lsof db.sqlite3
   ```

4. **Restart Services:**
   ```bash
   # Development
   # Just restart the Django server
   
   # Production with systemd
   sudo systemctl restart nohands nohands-celery
   ```

#### Issue 7: "Dockerfile Not Found"

**Symptoms:**
- Build fails with "Dockerfile not found"
- Error mentions missing Dockerfile

**Solutions:**
1. **Verify Dockerfile Path in Repository Config:**
   - Check the `dockerfile_path` field in repository settings
   - Default is `Dockerfile` (case-sensitive!)

2. **Check Dockerfile Location:**
   ```bash
   # Clone the repo locally and verify
   git clone <repository-url> test-clone
   cd test-clone
   ls -la Dockerfile  # Or the configured path
   ```

3. **Common Paths:**
   - Root: `Dockerfile`
   - Docker directory: `docker/Dockerfile`
   - Build directory: `build/Dockerfile`

4. **Update Repository Configuration:**
   - Admin → Git Repositories → Select repo → Edit
   - Update `Dockerfile Path` field

#### Issue 8: High Resource Usage

**Symptoms:**
- System slows down during builds
- High CPU or memory usage

**Solutions:**
1. **Limit Concurrent Builds:**
   ```bash
   export MAX_CONCURRENT_BUILDS=1
   ```

2. **Monitor Resources:**
   ```bash
   # CPU and Memory
   top
   
   # Docker resources
   docker stats
   ```

3. **Clean Up Old Builds:**
   ```bash
   # Remove old build directories
   find tmp/git_checkouts/builds -type d -mtime +7 -exec rm -rf {} \;
   
   # Clean Docker images
   docker image prune -a
   ```

4. **Configure Docker Resource Limits:**
   ```bash
   # Edit Docker daemon config
   sudo vim /etc/docker/daemon.json
   ```
   ```json
   {
     "max-concurrent-downloads": 3,
     "max-concurrent-uploads": 3
   }
   ```

#### Issue 9: API Returns 404 or 500 Errors

**Symptoms:**
- API endpoints return errors
- Cannot access API routes

**Solutions:**
1. **Verify URL Pattern:**
   ```bash
   # List all URLs
   python manage.py show_urls  # If django-extensions installed
   
   # Or check urls.py files
   cat nohands_project/urls.py
   cat api/urls.py
   ```

2. **Check Allowed Hosts:**
   ```python
   # settings.py
   ALLOWED_HOSTS = ['localhost', '127.0.0.1', 'your-domain.com']
   ```

3. **Enable Debug for Development:**
   ```bash
   export DJANGO_DEBUG=True
   # Restart server to see detailed error messages
   ```

4. **Check Django Logs:**
   ```bash
   # In runserver output or log files
   tail -f /var/log/nohands/django.log
   ```

### Getting Help

If you encounter issues not covered here:

1. **Check Django Logs:**
   - Development: Check console output
   - Production: Check log files

2. **Enable Debug Mode (Development Only):**
   ```bash
   export DJANGO_DEBUG=True
   python manage.py runserver
   ```

3. **Run Django Check:**
   ```bash
   python manage.py check
   python manage.py check --deploy  # Production checks
   ```

4. **Test Components Individually:**
   ```python
   # Test Git operations
   python manage.py shell
   >>> from projects.git_utils import clone_or_update_repo
   >>> from pathlib import Path
   >>> clone_or_update_repo("https://github.com/user/repo.git", Path("/tmp/test"))
   
   # Test Dagger
   >>> from builds.dagger_pipeline import run_build_sync
   >>> # Test build with small project
   ```

5. **Check GitHub Issues:**
   - Visit: https://github.com/vbrunelle/NoHands/issues
   - Search for similar problems
   - Open a new issue with:
     - Detailed error messages
     - Steps to reproduce
     - Environment information (OS, Python version, Docker version)

### Development

- Use Django's `check` command: `python manage.py check`
- Run tests: `python manage.py test`
- Use migrations for database changes
- Follow Django best practices

## 📋 Example Dockerfile

If your project doesn't have a Dockerfile, use `Dockerfile.example` as a template:

```dockerfile
# Example Dockerfile for a Python application
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies if needed
# RUN apt-get update && apt-get install -y some-package

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port (adjust as needed)
EXPOSE 8000

# Run the application
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
```

### Dockerfile Best Practices

1. **Use Specific Base Image Tags:**
   ```dockerfile
   FROM python:3.11-slim  # Good
   FROM python:latest     # Avoid
   ```

2. **Minimize Layers:**
   ```dockerfile
   # Good - single RUN command
   RUN apt-get update && apt-get install -y \
       package1 \
       package2 \
       && rm -rf /var/lib/apt/lists/*
   
   # Avoid - multiple RUN commands
   RUN apt-get update
   RUN apt-get install -y package1
   RUN apt-get install -y package2
   ```

3. **Use .dockerignore:**
   ```
   # .dockerignore
   __pycache__
   *.pyc
   *.pyo
   *.pyd
   .Python
   env/
   venv/
   .venv
   .git
   .gitignore
   .env
   *.sqlite3
   *.log
   node_modules/
   ```

4. **Multi-stage Builds (for compiled apps):**
   ```dockerfile
   # Build stage
   FROM node:18 AS builder
   WORKDIR /app
   COPY package*.json ./
   RUN npm ci
   COPY . .
   RUN npm run build
   
   # Production stage
   FROM nginx:alpine
   COPY --from=builder /app/dist /usr/share/nginx/html
   EXPOSE 80
   CMD ["nginx", "-g", "daemon off;"]
   ```

## 🐛 Troubleshooting

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

## 📚 Additional Resources

### Documentation

- **Django Documentation**: https://docs.djangoproject.com/
- **Django REST Framework**: https://www.django-rest-framework.org/
- **Dagger Documentation**: https://docs.dagger.io/
- **GitPython Documentation**: https://gitpython.readthedocs.io/
- **Docker Documentation**: https://docs.docker.com/

### Related Projects

- **Dagger**: https://dagger.io/ - Application delivery as code
- **Jenkins**: https://www.jenkins.io/ - Automation server
- **GitLab CI/CD**: https://docs.gitlab.com/ee/ci/ - GitLab's built-in CI/CD
- **GitHub Actions**: https://github.com/features/actions - GitHub's workflow automation
- **ArgoCD**: https://argo-cd.readthedocs.io/ - GitOps continuous delivery

### Tutorials and Guides

- **Django for Beginners**: https://djangoforbeginners.com/
- **Docker Tutorial**: https://docs.docker.com/get-started/
- **REST API Design**: https://restfulapi.net/
- **Git Basics**: https://git-scm.com/book/en/v2/Getting-Started-Git-Basics

## 🤝 Community

### Getting Help

- **GitHub Issues**: https://github.com/vbrunelle/NoHands/issues
- **Discussions**: Use GitHub Discussions for questions and ideas
- **Documentation**: Refer to this README and code comments

### Contributing

We welcome contributions! See the [Contributing](#-contributing) section above for guidelines.

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## 📜 License

This project is open source and available under the **MIT License**.

```
MIT License

Copyright (c) 2025 NoHands Contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## 🙏 Acknowledgments

NoHands is built with the following amazing open-source projects:

- **Django** - The web framework for perfectionists with deadlines
- **Django REST Framework** - Powerful and flexible toolkit for building Web APIs
- **Dagger** - Application delivery as code
- **GitPython** - Python library for interacting with Git repositories
- **Docker** - Platform for developing, shipping, and running applications

## 📞 Support

For issues and questions:
- **GitHub Issues**: https://github.com/vbrunelle/NoHands/issues
- **Documentation**: Refer to this comprehensive README

### Reporting Security Issues

If you discover a security vulnerability, please email the maintainers directly instead of opening a public issue. We take security seriously and will respond promptly.

## 🗺️ Roadmap

Future enhancements and features planned for NoHands:

### Short Term (Next Release)
- [ ] WebSocket support for real-time build logs
- [ ] Build queue management and prioritization
- [ ] Enhanced error reporting and debugging tools
- [ ] Docker Compose file support
- [ ] Build artifacts management

### Medium Term
- [ ] Celery integration for background tasks (production-ready)
- [ ] Multi-registry support (push to multiple registries)
- [ ] Build notifications (email, Slack, webhooks)
- [ ] Advanced build configurations (environment variables, build args)
- [ ] Build templates and presets

### Long Term
- [ ] Kubernetes deployment support
- [ ] Build caching and optimization
- [ ] Scheduled builds and recurring builds
- [ ] Build comparison and diffing
- [ ] Integration with CI/CD platforms (GitHub Actions, GitLab CI)
- [ ] Web-based Dockerfile editor
- [ ] Build analytics and metrics dashboard
- [ ] Multi-user support with role-based access control
- [ ] Build approval workflows

### Want to Help?

Check out our [Contributing](#-contributing) section to get started with any of these features!

## 📊 Project Stats

- **Language**: Python 3.11+
- **Framework**: Django 5.0+
- **License**: MIT
- **Status**: Active Development

## 🌟 Star History

If you find NoHands useful, please consider giving it a star on GitHub! ⭐

---

**Made with ❤️ by the NoHands community**

For more information, visit: https://github.com/vbrunelle/NoHands