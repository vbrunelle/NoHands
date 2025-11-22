# NoHands API Documentation

Complete reference for the NoHands REST API.

## Table of Contents

- [Overview](#overview)
- [Authentication](#authentication)
- [Base URL](#base-url)
- [Response Format](#response-format)
- [Pagination](#pagination)
- [Error Handling](#error-handling)
- [Endpoints](#endpoints)
  - [Repositories](#repositories)
  - [Branches](#branches)
  - [Commits](#commits)
  - [Builds](#builds)
- [Rate Limiting](#rate-limiting)
- [Code Examples](#code-examples)

## Overview

The NoHands REST API provides programmatic access to all features of the NoHands platform. You can:

- List and manage Git repositories
- Browse branches and commits
- Trigger and monitor Docker image builds
- Retrieve build logs and status
- Integrate with CI/CD pipelines

**API Version**: v1  
**Content Type**: `application/json`  
**Base URL**: `http://localhost:8000/api/`

## Authentication

### Current Implementation

The API currently uses Django's session authentication. For production deployments, consider implementing token-based authentication.

### Session Authentication

```bash
# Login via Django admin
curl -c cookies.txt -X POST http://localhost:8000/admin/login/ \
  -d "username=admin&password=your-password"

# Use cookies for API requests
curl -b cookies.txt http://localhost:8000/api/repositories/
```

### Token Authentication (Optional)

To enable token authentication, update `settings.py`:

```python
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
}
```

Then use tokens in requests:

```bash
curl -H "Authorization: Token your-token-here" \
  http://localhost:8000/api/repositories/
```

## Base URL

All API endpoints are relative to:

```
http://localhost:8000/api/
```

For production:
```
https://your-domain.com/api/
```

## Response Format

### Success Response

```json
{
  "count": 10,
  "next": "http://localhost:8000/api/repositories/?page=2",
  "previous": null,
  "results": [
    {
      "id": 1,
      "name": "my-app",
      "url": "https://github.com/user/my-app.git",
      ...
    }
  ]
}
```

### Single Object Response

```json
{
  "id": 1,
  "name": "my-app",
  "url": "https://github.com/user/my-app.git",
  ...
}
```

## Pagination

All list endpoints are paginated with 20 results per page by default.

### Pagination Parameters

- `page` - Page number (default: 1)
- `page_size` - Results per page (max: 100)

### Pagination Response

```json
{
  "count": 45,                                        // Total results
  "next": "http://localhost:8000/api/repositories/?page=2",  // Next page URL
  "previous": null,                                   // Previous page URL
  "results": [...]                                    // Current page results
}
```

### Example

```bash
# Get page 2
curl "http://localhost:8000/api/repositories/?page=2"

# Get 50 results per page
curl "http://localhost:8000/api/repositories/?page_size=50"
```

## Error Handling

### HTTP Status Codes

| Code | Meaning |
|------|---------|
| 200 | OK - Request successful |
| 201 | Created - Resource created successfully |
| 400 | Bad Request - Invalid parameters |
| 404 | Not Found - Resource doesn't exist |
| 500 | Internal Server Error - Server error |

### Error Response Format

```json
{
  "error": "Error message describing what went wrong"
}
```

Or for validation errors:

```json
{
  "field_name": ["Error message for this field"],
  "another_field": ["Another error message"]
}
```

### Example Error Responses

**404 Not Found:**
```json
{
  "error": "Repository not found"
}
```

**400 Bad Request:**
```json
{
  "repository_id": ["This field is required."],
  "commit_id": ["This field is required."]
}
```

## Endpoints

### Repositories

Manage Git repositories.

#### List Repositories

```
GET /api/repositories/
```

**Parameters:** None

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
    }
  ]
}
```

**Example:**
```bash
curl http://localhost:8000/api/repositories/
```

#### Get Repository Details

```
GET /api/repositories/{id}/
```

**Parameters:**
- `id` (path) - Repository ID

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

**Example:**
```bash
curl http://localhost:8000/api/repositories/1/
```

**Status Codes:**
- `200` - Success
- `404` - Repository not found

---

### Branches

Browse repository branches.

#### List Branches

```
GET /api/branches/
```

**Query Parameters:**
- `repository` (optional) - Filter by repository ID

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
    }
  ]
}
```

**Examples:**
```bash
# All branches
curl http://localhost:8000/api/branches/

# Branches for specific repository
curl "http://localhost:8000/api/branches/?repository=1"
```

#### Get Branch Details

```
GET /api/branches/{id}/
```

**Parameters:**
- `id` (path) - Branch ID

**Response:**
```json
{
  "id": 1,
  "repository_name": "my-app",
  "name": "main",
  "commit_sha": "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0",
  "last_updated": "2025-01-15T12:00:00Z"
}
```

**Example:**
```bash
curl http://localhost:8000/api/branches/1/
```

---

### Commits

Browse repository commits.

#### List Commits

```
GET /api/commits/
```

**Query Parameters:**
- `repository` (optional) - Filter by repository ID
- `branch` (optional) - Filter by branch ID

**Response:**
```json
{
  "count": 50,
  "next": "http://localhost:8000/api/commits/?page=2",
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
    }
  ]
}
```

**Examples:**
```bash
# All commits
curl http://localhost:8000/api/commits/

# Commits for specific repository
curl "http://localhost:8000/api/commits/?repository=1"

# Commits for specific branch
curl "http://localhost:8000/api/commits/?branch=1"

# Commits for specific repository and branch
curl "http://localhost:8000/api/commits/?repository=1&branch=1"
```

#### Get Commit Details

```
GET /api/commits/{id}/
```

**Parameters:**
- `id` (path) - Commit ID

**Response:**
```json
{
  "id": 101,
  "repository_name": "my-app",
  "branch_name": "main",
  "sha": "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0",
  "message": "Add new feature",
  "author": "John Doe",
  "author_email": "john@example.com",
  "committed_at": "2025-01-15T14:30:00Z"
}
```

**Example:**
```bash
curl http://localhost:8000/api/commits/101/
```

---

### Builds

Trigger and monitor Docker image builds.

#### List Builds

```
GET /api/builds/
```

**Query Parameters:**
- `repository` (optional) - Filter by repository ID
- `status` (optional) - Filter by status (`pending`, `running`, `success`, `failed`)

**Response:**
```json
{
  "count": 10,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 42,
      "repository_name": "my-app",
      "commit_sha": "a1b2c3d4",
      "branch_name": "main",
      "status": "success",
      "image_tag": "my-app:a1b2c3d4",
      "logs": "Build logs...",
      "error_message": "",
      "created_at": "2025-01-15T15:00:00Z",
      "started_at": "2025-01-15T15:00:05Z",
      "completed_at": "2025-01-15T15:02:10Z",
      "push_to_registry": true,
      "duration": "2m 5s"
    }
  ]
}
```

**Examples:**
```bash
# All builds
curl http://localhost:8000/api/builds/

# Builds for specific repository
curl "http://localhost:8000/api/builds/?repository=1"

# Successful builds only
curl "http://localhost:8000/api/builds/?status=success"

# Failed builds for specific repository
curl "http://localhost:8000/api/builds/?repository=1&status=failed"
```

#### Get Build Details

```
GET /api/builds/{id}/
```

**Parameters:**
- `id` (path) - Build ID

**Response:**
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
  "push_to_registry": true,
  "duration": "2m 5s"
}
```

**Example:**
```bash
curl http://localhost:8000/api/builds/42/
```

#### Trigger Build

```
POST /api/builds/trigger/
```

**Request Body:**
```json
{
  "repository_id": 1,
  "commit_id": 101,
  "push_to_registry": false,
  "deploy_after_build": false
}
```

**Request Fields:**
- `repository_id` (required) - Repository ID
- `commit_id` (required) - Commit ID
- `push_to_registry` (optional, default: false) - Whether to push to Docker registry
- `deploy_after_build` (optional, default: false) - Whether to deploy after successful build

**Response (201 Created):**
```json
{
  "id": 43,
  "repository_name": "my-app",
  "commit_sha": "a1b2c3d4",
  "branch_name": "main",
  "status": "pending",
  "image_tag": "",
  "logs": "",
  "error_message": "",
  "created_at": "2025-01-15T16:00:00Z",
  "started_at": null,
  "completed_at": null,
  "push_to_registry": false,
  "duration": "N/A"
}
```

**Example:**
```bash
curl -X POST http://localhost:8000/api/builds/trigger/ \
  -H "Content-Type: application/json" \
  -d '{
    "repository_id": 1,
    "commit_id": 101,
    "push_to_registry": true,
    "deploy_after_build": false
  }'
```

**Status Codes:**
- `201` - Build created and started
- `400` - Invalid request (missing fields, invalid IDs)
- `404` - Repository or commit not found

**Error Response (400):**
```json
{
  "repository_id": ["This field is required."],
  "commit_id": ["This field is required."]
}
```

**Error Response (404):**
```json
{
  "error": "Repository not found"
}
```

```json
{
  "error": "Commit not found"
}
```

---

## Rate Limiting

Currently, there is no rate limiting implemented. For production deployments, consider implementing rate limiting using packages like `django-ratelimit`.

**Recommended Implementation:**

```python
# settings.py
RATELIMIT_ENABLE = True
RATELIMIT_VIEW = 'api.views.ratelimit_error'

# views.py
from django_ratelimit.decorators import ratelimit

@ratelimit(key='ip', rate='100/h')
def api_view(request):
    # Your view logic
    pass
```

## Code Examples

### Python

```python
import requests

class NoHandsClient:
    def __init__(self, base_url, token=None):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        if token:
            self.session.headers.update({
                'Authorization': f'Token {token}'
            })
    
    def list_repositories(self):
        """List all repositories."""
        response = self.session.get(f"{self.base_url}/api/repositories/")
        response.raise_for_status()
        return response.json()
    
    def get_repository(self, repo_id):
        """Get repository details."""
        response = self.session.get(f"{self.base_url}/api/repositories/{repo_id}/")
        response.raise_for_status()
        return response.json()
    
    def list_branches(self, repository_id=None):
        """List branches, optionally filtered by repository."""
        params = {'repository': repository_id} if repository_id else {}
        response = self.session.get(f"{self.base_url}/api/branches/", params=params)
        response.raise_for_status()
        return response.json()
    
    def list_commits(self, repository_id=None, branch_id=None):
        """List commits, optionally filtered by repository and/or branch."""
        params = {}
        if repository_id:
            params['repository'] = repository_id
        if branch_id:
            params['branch'] = branch_id
        response = self.session.get(f"{self.base_url}/api/commits/", params=params)
        response.raise_for_status()
        return response.json()
    
    def trigger_build(self, repository_id, commit_id, push_to_registry=False):
        """Trigger a new build."""
        data = {
            'repository_id': repository_id,
            'commit_id': commit_id,
            'push_to_registry': push_to_registry,
            'deploy_after_build': False
        }
        response = self.session.post(
            f"{self.base_url}/api/builds/trigger/",
            json=data
        )
        response.raise_for_status()
        return response.json()
    
    def get_build(self, build_id):
        """Get build details."""
        response = self.session.get(f"{self.base_url}/api/builds/{build_id}/")
        response.raise_for_status()
        return response.json()
    
    def list_builds(self, repository_id=None, status=None):
        """List builds, optionally filtered by repository and/or status."""
        params = {}
        if repository_id:
            params['repository'] = repository_id
        if status:
            params['status'] = status
        response = self.session.get(f"{self.base_url}/api/builds/", params=params)
        response.raise_for_status()
        return response.json()
    
    def wait_for_build(self, build_id, timeout=3600, poll_interval=10):
        """Wait for build to complete."""
        import time
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            build = self.get_build(build_id)
            status = build['status']
            
            if status == 'success':
                return build
            elif status == 'failed':
                raise Exception(f"Build failed: {build['error_message']}")
            
            time.sleep(poll_interval)
        
        raise TimeoutError(f"Build {build_id} timed out")

# Usage example
client = NoHandsClient("http://localhost:8000")

# List repositories
repos = client.list_repositories()
print(f"Found {repos['count']} repositories")

# Trigger a build
build = client.trigger_build(repository_id=1, commit_id=101, push_to_registry=True)
print(f"Build #{build['id']} triggered")

# Wait for completion
result = client.wait_for_build(build['id'])
print(f"Build completed: {result['image_tag']}")
```

### JavaScript/Node.js

```javascript
const axios = require('axios');

class NoHandsClient {
  constructor(baseUrl, token = null) {
    this.baseUrl = baseUrl.replace(/\/$/, '');
    this.client = axios.create({
      baseURL: this.baseUrl,
      headers: token ? { 'Authorization': `Token ${token}` } : {}
    });
  }

  async listRepositories() {
    const response = await this.client.get('/api/repositories/');
    return response.data;
  }

  async getRepository(repoId) {
    const response = await this.client.get(`/api/repositories/${repoId}/`);
    return response.data;
  }

  async listBranches(repositoryId = null) {
    const params = repositoryId ? { repository: repositoryId } : {};
    const response = await this.client.get('/api/branches/', { params });
    return response.data;
  }

  async listCommits(repositoryId = null, branchId = null) {
    const params = {};
    if (repositoryId) params.repository = repositoryId;
    if (branchId) params.branch = branchId;
    const response = await this.client.get('/api/commits/', { params });
    return response.data;
  }

  async triggerBuild(repositoryId, commitId, pushToRegistry = false) {
    const response = await this.client.post('/api/builds/trigger/', {
      repository_id: repositoryId,
      commit_id: commitId,
      push_to_registry: pushToRegistry,
      deploy_after_build: false
    });
    return response.data;
  }

  async getBuild(buildId) {
    const response = await this.client.get(`/api/builds/${buildId}/`);
    return response.data;
  }

  async listBuilds(repositoryId = null, status = null) {
    const params = {};
    if (repositoryId) params.repository = repositoryId;
    if (status) params.status = status;
    const response = await this.client.get('/api/builds/', { params });
    return response.data;
  }

  async waitForBuild(buildId, timeout = 3600000, pollInterval = 10000) {
    const startTime = Date.now();
    
    while (Date.now() - startTime < timeout) {
      const build = await this.getBuild(buildId);
      const status = build.status;
      
      if (status === 'success') {
        return build;
      } else if (status === 'failed') {
        throw new Error(`Build failed: ${build.error_message}`);
      }
      
      await new Promise(resolve => setTimeout(resolve, pollInterval));
    }
    
    throw new Error(`Build ${buildId} timed out`);
  }
}

// Usage example
(async () => {
  const client = new NoHandsClient('http://localhost:8000');
  
  // List repositories
  const repos = await client.listRepositories();
  console.log(`Found ${repos.count} repositories`);
  
  // Trigger a build
  const build = await client.triggerBuild(1, 101, true);
  console.log(`Build #${build.id} triggered`);
  
  // Wait for completion
  const result = await client.waitForBuild(build.id);
  console.log(`Build completed: ${result.image_tag}`);
})();
```

### Bash

```bash
#!/bin/bash
# nohands-client.sh - Bash client for NoHands API

NOHANDS_URL="${NOHANDS_URL:-http://localhost:8000}"

# List repositories
list_repositories() {
  curl -s "${NOHANDS_URL}/api/repositories/" | jq '.'
}

# Get repository
get_repository() {
  local repo_id=$1
  curl -s "${NOHANDS_URL}/api/repositories/${repo_id}/" | jq '.'
}

# List branches for repository
list_branches() {
  local repo_id=$1
  curl -s "${NOHANDS_URL}/api/branches/?repository=${repo_id}" | jq '.'
}

# List commits for branch
list_commits() {
  local branch_id=$1
  curl -s "${NOHANDS_URL}/api/commits/?branch=${branch_id}" | jq '.'
}

# Trigger build
trigger_build() {
  local repo_id=$1
  local commit_id=$2
  local push_to_registry=${3:-false}
  
  curl -s -X POST "${NOHANDS_URL}/api/builds/trigger/" \
    -H "Content-Type: application/json" \
    -d "{
      \"repository_id\": ${repo_id},
      \"commit_id\": ${commit_id},
      \"push_to_registry\": ${push_to_registry}
    }" | jq '.'
}

# Get build status
get_build() {
  local build_id=$1
  curl -s "${NOHANDS_URL}/api/builds/${build_id}/" | jq '.'
}

# Wait for build to complete
wait_for_build() {
  local build_id=$1
  local timeout=${2:-3600}
  local start_time=$(date +%s)
  
  while true; do
    local build=$(get_build "$build_id")
    local status=$(echo "$build" | jq -r '.status')
    
    echo "Build status: $status"
    
    if [ "$status" = "success" ]; then
      echo "Build completed successfully!"
      echo "$build" | jq '.'
      return 0
    elif [ "$status" = "failed" ]; then
      echo "Build failed!"
      echo "$build" | jq -r '.error_message'
      return 1
    fi
    
    local current_time=$(date +%s)
    local elapsed=$((current_time - start_time))
    
    if [ $elapsed -gt $timeout ]; then
      echo "Build timed out after ${timeout}s"
      return 1
    fi
    
    sleep 10
  done
}

# Usage example
case "${1:-help}" in
  list-repos)
    list_repositories
    ;;
  get-repo)
    get_repository "$2"
    ;;
  list-branches)
    list_branches "$2"
    ;;
  list-commits)
    list_commits "$2"
    ;;
  trigger-build)
    trigger_build "$2" "$3" "$4"
    ;;
  get-build)
    get_build "$2"
    ;;
  wait-build)
    wait_for_build "$2" "$3"
    ;;
  *)
    echo "Usage: $0 {list-repos|get-repo|list-branches|list-commits|trigger-build|get-build|wait-build}"
    echo ""
    echo "Examples:"
    echo "  $0 list-repos"
    echo "  $0 get-repo 1"
    echo "  $0 list-branches 1"
    echo "  $0 list-commits 1"
    echo "  $0 trigger-build 1 101 true"
    echo "  $0 get-build 42"
    echo "  $0 wait-build 42 600"
    ;;
esac
```

## Versioning

The API follows semantic versioning. Breaking changes will result in a new API version.

**Current Version**: v1

Future versions will be available at:
```
http://localhost:8000/api/v2/
```

## Support

For API questions and issues:
- GitHub Issues: https://github.com/vbrunelle/NoHands/issues
- Documentation: https://github.com/vbrunelle/NoHands

## Changelog

### v1.0.0 (Current)
- Initial API release
- Repositories, branches, commits, and builds endpoints
- Build triggering and monitoring
- Pagination support
- Session authentication
