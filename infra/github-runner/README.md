# GitHub Self-Hosted Runner

A Docker-based GitHub Actions self-hosted runner that automatically registers with your repository.

## Setup

### 1. Environment Configuration

Copy the example environment file and fill in your details:

```bash
cp .env.example .env
```

Edit `.env` with your GitHub information:

```
GH_TOKEN=ghp_your_personal_access_token_here
GH_OWNER=your-github-username-or-org
GH_REPOSITORY=your-repository-name
DOCKER_GID=999  # See Docker Socket Permissions section below
```

#### Docker Socket Permissions

The runner needs access to the host's Docker daemon. The `DOCKER_GID` must match your host machine's docker group ID.

Find your host's docker group ID:
```bash
ls -ln /var/run/docker.sock
```

Look for the group ID (third number). For example:
- `srw-rw---- 1 0 988 ...` means GID is 988
- `srw-rw---- 1 0 1001 ...` means GID is 1001

Set `DOCKER_GID` in your `.env` file to match this number. If you don't set it, it defaults to 999.

### 2. GitHub Personal Access Token

Create a Personal Access Token (PAT) with the required permissions:

1. Go to GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)
2. Click "Generate new token (classic)"
3. Select scopes:
   - **`repo`** (Full control of private repositories) - Required for repository-level runners
   - **read:org** (i think)
4. Copy the generated token and paste it in your `.env` file

**Important:** You must have **admin access** to the target repository for runner registration to work.

### 3. Repository Verification

Verify your repository exists and you have access:

```bash
curl -H "Authorization: token YOUR_TOKEN" https://api.github.com/repos/YOUR_OWNER/YOUR_REPO
```

Look for `"permissions": {"admin": true}` in the response.

## Usage

### Docker Compose (Recommended)

```bash
# Build and start the runner
docker-compose up --build

# Run in background
docker-compose up --build -d

# Stop the runner
docker-compose down
```

### Removing/Cleaning Up Runners

Should not reaaaaly be needed any more, as the runners should resume

If you get "A runner exists with the same name" errors, clean up orphaned runners:

```bash
# List runners to see what exists
gh api repos/YOUR_OWNER/YOUR_REPO/actions/runners

# Remove a specific runner by ID
gh api -X DELETE repos/YOUR_OWNER/YOUR_REPO/actions/runners/RUNNER_ID

# Remove all runners at once (cleanup script)
gh api repos/YOUR_OWNER/YOUR_REPO/actions/runners | jq -r '.runners[].id' | xargs -I {} gh api -X DELETE repos/YOUR_OWNER/YOUR_REPO/actions/runners/{}
```

**Note:** The Docker-based remove scripts don't work reliably. Always use the GitHub CLI for cleanup.

### Multiple Runners

For parallel job execution, use the multi-runner compose file:

```bash
# Start 5 parallel runners
docker-compose -f docker-compose.multi.yml up --build

# Stop all runners
docker-compose -f docker-compose.multi.yml down
```

### Direct Docker

```bash
# Build the image
docker build -t my-github-runner .

# Run the container
docker run -e GH_TOKEN='your_token' -e GH_OWNER='your_owner' -e GH_REPOSITORY='your_repo' my-github-runner
```

## How It Works

1. **Token Generation**: The runner requests a registration token from GitHub's API
2. **Self-Registration**: Uses the token to register itself with your repository
3. **Job Execution**: Listens for and executes GitHub Actions jobs
4. **Auto-Restart**: Container restarts automatically if it crashes

## Troubleshooting

### Docker Permission Denied Error
```
permission denied while trying to connect to the Docker daemon socket at unix:///var/run/docker.sock
```

This means the `DOCKER_GID` in your `.env` doesn't match your host's docker group ID. See the Docker Socket Permissions section above to fix this.

### 404 Not Found Error
- Verify your repository name is correct (check for typos!)
- Ensure you have admin access to the repository
- Check that your PAT has `repo` scope

### Permission Denied
- Verify your GitHub token has admin permissions on the target repository
- Ensure the token hasn't expired

### .NET/ICU Errors
- The Dockerfile includes `libicu70` for .NET Core support
- If you see ICU-related errors, the base image may need updates

## Architecture

```
┌─────────────────┐    ┌──────────────┐    ┌─────────────────┐
│   Docker        │    │   GitHub     │    │   Repository    │
│   Container     │───▶│   API        │───▶│   Actions       │
│                 │    │              │    │   Runner        │
│ - Ubuntu 22.04  │    │ Registration │    │                 │
│ - GitHub Runner │    │ Token        │    │ Executes Jobs   │
│ - Dependencies  │    │              │    │                 │
└─────────────────┘    └──────────────┘    └─────────────────┘
```

## Security Notes

- Keep your `.env` file secure and never commit it to version control
- Rotate your GitHub Personal Access Tokens regularly
- The runner runs as a non-root user inside the container
- Consider using GitHub Apps for production deployments instead of PATs

## Files

- `dockerfile` - Container definition
- `docker-compose.yml` - Orchestration configuration
- `scripts/start.sh` - Runner initialization script
- `.env.example` - Environment template
- `.env` - Your configuration (git-ignored)