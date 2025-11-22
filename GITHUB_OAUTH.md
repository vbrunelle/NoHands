# GitHub OAuth Integration

This document explains how to set up and use the GitHub OAuth integration for connecting repositories.

## Overview

NoHands now supports GitHub OAuth authentication, allowing users to:
- Login with their GitHub account
- Browse their GitHub repositories
- Connect repositories directly from the web interface
- Avoid manually entering repository URLs and credentials

## Setup

### 1. Create a GitHub OAuth App

1. Go to GitHub Settings → Developer settings → OAuth Apps
2. Click "New OAuth App"
3. Fill in the application details:
   - **Application name**: NoHands (or your preferred name)
   - **Homepage URL**: `http://localhost:8000` (or your domain)
   - **Authorization callback URL**: `http://localhost:8000/accounts/github/login/callback/`
4. Click "Register application"
5. Note your **Client ID** and generate a **Client Secret**

### 2. Configure NoHands

Set the following environment variables:

```bash
export GITHUB_CLIENT_ID="your_github_client_id"
export GITHUB_CLIENT_SECRET="your_github_client_secret"
```

Or add them to your `.env` file:

```bash
GITHUB_CLIENT_ID=your_github_client_id
GITHUB_CLIENT_SECRET=your_github_client_secret
```

### 3. Configure Social Application in Django Admin

1. Start the Django server: `python manage.py runserver`
2. Go to Django Admin: `http://localhost:8000/admin/`
3. Navigate to **Social Applications** under **Sites**
4. Click **Add Social Application**
5. Fill in the form:
   - **Provider**: GitHub
   - **Name**: GitHub (or any name you prefer)
   - **Client id**: Your GitHub OAuth App Client ID
   - **Secret key**: Your GitHub OAuth App Client Secret
   - **Sites**: Select your site (usually `example.com` or create a new one)
6. Click **Save**

### 4. Create a Site (if needed)

If you don't have a site configured:

1. Go to Django Admin: `http://localhost:8000/admin/`
2. Navigate to **Sites**
3. Edit the default site or add a new one:
   - **Domain name**: `localhost:8000` (for development) or your domain
   - **Display name**: NoHands
4. Click **Save**

## Usage

### For Users

#### 1. Login with GitHub

1. Navigate to NoHands: `http://localhost:8000/`
2. Click the **"Login with GitHub"** button in the top navigation
3. You'll be redirected to GitHub to authorize the application
4. After authorization, you'll be logged in to NoHands

#### 2. Connect a Repository

1. Once logged in, go to the **Repositories** page
2. Click **"Connect GitHub Repo"** button
3. You'll see a list of all your GitHub repositories
4. Click **"Connect Repository"** on any repository you want to add
5. The repository will be added to NoHands and associated with your account

#### 3. Build from Connected Repository

1. Navigate to the connected repository's detail page
2. Click **"Refresh Branches"** to fetch branches
3. Select a branch and **"Refresh Commits"** to see commits
4. Click **"Build"** on any commit to trigger a build

### For Administrators

#### Manual Repository Addition

Administrators can still add repositories manually through the Django Admin interface:

1. Go to Django Admin: `http://localhost:8000/admin/`
2. Navigate to **Git Repositories**
3. Click **Add Git Repository**
4. Fill in the repository details manually
5. Click **Save**

## Features

### User Association

- Repositories connected via GitHub OAuth are associated with the user who connected them
- The repository list shows who connected each repository
- This enables future features like user-specific repository filtering and permissions

### Security

- OAuth tokens are securely stored and managed by django-allauth
- Users only grant access to their own repositories
- Tokens can be revoked at any time from GitHub settings

### Supported Repository Types

- Public repositories
- Private repositories (if the user has access)
- Organization repositories (if the user is a member)

## Troubleshooting

### "Please connect your GitHub account first" error

**Cause**: You're logged in but haven't connected your GitHub account.

**Solution**: 
1. Logout from NoHands
2. Click "Login with GitHub" and authorize the application
3. Try connecting a repository again

### No repositories showing up

**Possible causes**:
1. You don't have any repositories on GitHub
2. The OAuth token doesn't have the required scopes
3. There was an error fetching repositories

**Solution**:
1. Check that you have repositories on GitHub
2. Verify the OAuth app has `repo` and `user` scopes
3. Check the Django logs for any error messages
4. Try disconnecting and reconnecting your GitHub account

### "Repository already exists" warning

**Cause**: The repository is already connected to NoHands.

**Solution**: Go to the Repositories page and find the existing repository. You don't need to connect it again.

### OAuth callback URL mismatch

**Cause**: The callback URL in your GitHub OAuth App doesn't match your application's URL.

**Solution**: 
1. Go to your GitHub OAuth App settings
2. Update the **Authorization callback URL** to match your application:
   - Development: `http://localhost:8000/accounts/github/login/callback/`
   - Production: `https://yourdomain.com/accounts/github/login/callback/`

## API Access

The GitHub integration works seamlessly with the existing REST API. Connected repositories appear in the API just like manually added repositories:

```bash
# List all repositories
curl http://localhost:8000/api/repositories/

# Get repository details
curl http://localhost:8000/api/repositories/1/
```

## Future Enhancements

Planned improvements for the GitHub integration:

- [ ] Automatic webhook setup for CI/CD
- [ ] GitHub status checks integration
- [ ] Pull request build triggers
- [ ] Organization repository filtering
- [ ] Team-based access control
- [ ] GitHub Actions integration

## Support

For issues or questions:
- Check the main README.md file
- Open an issue on GitHub: https://github.com/vbrunelle/NoHands/issues
- Check Django logs for detailed error messages

## Security Considerations

### Production Deployment

When deploying to production:

1. **Use HTTPS**: Always use HTTPS for the callback URL
2. **Secure Secrets**: Store GitHub OAuth credentials in environment variables, not in code
3. **Regular Updates**: Keep django-allauth and PyGithub up to date
4. **Token Expiration**: Consider implementing token refresh logic
5. **Rate Limiting**: GitHub API has rate limits; implement caching where appropriate

### Token Storage

- OAuth tokens are stored in the database by django-allauth
- Ensure your database is properly secured
- Consider encrypting sensitive database fields in production
- Implement regular database backups

## Technical Details

### Dependencies

- `django-allauth>=0.57.0`: Handles OAuth authentication
- `PyGithub>=2.1.1`: GitHub API client library

### Database Schema

The `GitRepository` model has been extended with:
- `user`: ForeignKey to User (nullable for backward compatibility)
- `github_id`: CharField to store GitHub repository ID

### Views

- `connect_github_repository`: Displays GitHub repositories and handles connection
- Updated `repository_list`: Shows login/connect buttons based on authentication status

### Templates

- `connect_github.html`: Repository selection interface
- Updated `repository_list.html`: Added GitHub login/connect buttons
- Updated `base.html`: User authentication UI in navbar

### URL Configuration

- `/accounts/`: Django-allauth URLs (login, logout, social auth)
- `/repositories/connect/`: GitHub repository connection interface

## License

This feature is part of NoHands and is covered by the MIT License.
