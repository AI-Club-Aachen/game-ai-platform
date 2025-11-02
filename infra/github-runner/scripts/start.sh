#!/bin/bash
GH_OWNER=$GH_OWNER
GH_REPOSITORY=$GH_REPOSITORY
GH_TOKEN=$GH_TOKEN

cd /home/runner

echo "Checking for existing runner configuration..."
ls -la

# Always try to remove any existing runner configuration first
echo "Attempting to remove any existing runner..."
REG_TOKEN=$(curl -sX POST -H "Accept: application/vnd.github.v3+json" -H "Authorization: token ${GH_TOKEN}" https://api.github.com/repos/${GH_OWNER}/${GH_REPOSITORY}/actions/runners/registration-token | jq .token --raw-output)

# Try to remove configuration regardless of .runner file existence
./config.sh remove --unattended --token ${REG_TOKEN} 2>/dev/null || echo "No existing runner to remove (this is normal on first run)"

# Clean up any leftover configuration files
rm -f .runner .credentials .credentials_rsaparams

echo "Configuring new runner..."
# Create unique runner name with timestamp to avoid conflicts
UNIQUE_RUNNER_NAME="${RUNNER_NAME:-dockerNode}-$(date +%s)"
echo "Using runner name: $UNIQUE_RUNNER_NAME"

# Get fresh registration token and configure runner
REG_TOKEN=$(curl -sX POST -H "Accept: application/vnd.github.v3+json" -H "Authorization: token ${GH_TOKEN}" https://api.github.com/repos/${GH_OWNER}/${GH_REPOSITORY}/actions/runners/registration-token | jq .token --raw-output)
./config.sh --unattended --url https://github.com/${GH_OWNER}/${GH_REPOSITORY} --token ${REG_TOKEN} --name "${UNIQUE_RUNNER_NAME}"

echo "Starting runner..."
./run.sh
