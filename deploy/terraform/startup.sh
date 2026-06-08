#!/bin/bash
# Startup script for Container-Optimized OS (COS) instances running a Docker-based worker.

set -o errexit
set -o nounset
set -o pipefail

echo "==========================================="
echo "Starting Game Worker Initialization Script"
echo "==========================================="

# Metadata server base URL for custom attributes
METADATA_URL="http://metadata.google.internal/computeMetadata/v1/instance/attributes"

# Helper function to fetch instance metadata values
fetch_metadata() {
  local key="$1"
  curl -s -f -H "Metadata-Flavor: Google" "${METADATA_URL}/${key}"
}

# 1. Fetch parameters from metadata server
echo "Fetching configuration from metadata server..."
BACKEND_URL=$(fetch_metadata "backend_url" || echo "")
REDIS_URL=$(fetch_metadata "redis_url" || echo "")
WORKER_TOKEN=$(fetch_metadata "worker_token" || echo "")
WORKER_IMAGE=$(fetch_metadata "worker_image" || echo "")

# 2. Fail-fast validation
MISSING_KEYS=()
[ -z "${BACKEND_URL}" ] && MISSING_KEYS+=("backend_url")
[ -z "${REDIS_URL}" ] && MISSING_KEYS+=("redis_url")
[ -z "${WORKER_TOKEN}" ] && MISSING_KEYS+=("worker_token")
[ -z "${WORKER_IMAGE}" ] && MISSING_KEYS+=("worker_image")

if [ ${#MISSING_KEYS[@]} -ne 0 ]; then
  echo "CRITICAL ERROR: The following required metadata attributes are missing: ${MISSING_KEYS[*]}" >&2
  exit 1
fi

echo "All required metadata values verified."
echo "Worker Image: ${WORKER_IMAGE}"
echo "Backend URL: ${BACKEND_URL}"

# 3. Authenticate with GCP Artifact Registry / Container Registry if needed
# Container-Optimized OS has docker-credential-gcr built-in, which configures
# Docker to use the instance service account credentials to pull from GCP registries.
if [[ "${WORKER_IMAGE}" =~ gcr.io || "${WORKER_IMAGE}" =~ pkg.dev ]]; then
  echo "Configuring Docker credentials helper for GCP registries..."
  docker-credential-gcr configure-docker --registries="${WORKER_IMAGE%%/*}" || true
fi

# 4. Pull worker image
echo "Pulling worker container image: ${WORKER_IMAGE}..."
if ! docker pull "${WORKER_IMAGE}"; then
  echo "CRITICAL ERROR: Failed to pull Docker image ${WORKER_IMAGE}" >&2
  exit 1
fi

# 5. Stop and clean up existing container if any (ensures idempotency on restart/reboot)
CONTAINER_NAME="game-worker"
if docker ps -a --format '{{.Names}}' | grep -Eq "^${CONTAINER_NAME}$"; then
  echo "Found existing container '${CONTAINER_NAME}'. Stopping and removing..."
  docker stop "${CONTAINER_NAME}" || true
  docker rm "${CONTAINER_NAME}" || true
fi

# 6. Start the worker container
# Standard output/error from the container will go to journald,
# which Container-Optimized OS automatically forwards to Google Cloud Logging.
echo "Launching worker container..."
docker run -d \
  --name "${CONTAINER_NAME}" \
  --restart unless-stopped \
  -e BACKEND_URL="${BACKEND_URL}" \
  -e REDIS_URL="${REDIS_URL}" \
  -e WORKER_TOKEN="${WORKER_TOKEN}" \
  "${WORKER_IMAGE}"

echo "==========================================="
echo "Game Worker Initialization Completed Successfully"
echo "==========================================="
