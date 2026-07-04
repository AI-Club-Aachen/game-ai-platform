#!/usr/bin/env bash
# get_deployed_logs.sh - Fetches logs from the GCE deployed backend and worker containers.

set -euo pipefail

# Print usage instructions
usage() {
    echo "Usage: $0 -p <project-id> -z <zone> -o <local-output-dir>"
    echo "  -p  GCP Project ID (required)"
    echo "  -z  GCP Zone (required)"
    echo "  -o  Local directory to save logs (required)"
    exit 1
}

PROJECT=""
ZONE=""
OUTPUT_DIR=""

while getopts "p:z:o:h" opt; do
    case "$opt" in
        p) PROJECT=$OPTARG ;;
        z) ZONE=$OPTARG ;;
        o) OUTPUT_DIR=$OPTARG ;;
        h|*) usage ;;
    esac
done

if [ -z "$PROJECT" ] || [ -z "$ZONE" ] || [ -z "$OUTPUT_DIR" ]; then
    echo "Error: Missing required arguments."
    usage
fi

# Create output directory
mkdir -p "$OUTPUT_DIR"
echo "Fetching logs into local directory: $OUTPUT_DIR"

# 1. Fetch Backend VM startup and service logs
echo "----------------------------------------"
echo "Connecting to backend VM (backend)..."
echo "----------------------------------------"

# Startup script logs
echo "Fetching /var/log/backend-startup.log..."
gcloud compute ssh backend --zone="$ZONE" --project="$PROJECT" \
    --command="sudo cat /var/log/backend-startup.log" > "$OUTPUT_DIR/backend-startup.log" 2>/dev/null || \
    echo "Warning: Could not fetch backend-startup.log"

# Docker Compose logs for each service
SERVICES=(nginx db redis frontend backend agent-builder)
for service in "${SERVICES[@]}"; do
    echo "Fetching backend docker logs for: $service..."
    gcloud compute ssh backend --zone="$ZONE" --project="$PROJECT" \
        --command="cd /opt/gameai && sudo docker compose logs --no-color --tail=5000 $service" > "$OUTPUT_DIR/backend_$service.log" 2>/dev/null || \
        echo "Warning: Could not fetch logs for backend service: $service"
done

# 2. Fetch logs from all worker instances
echo "----------------------------------------"
echo "Finding active worker VMs..."
echo "----------------------------------------"

WORKERS=$(gcloud compute instances list --project="$PROJECT" --filter="name~game-worker" --format="value(name,zone)")

if [ -z "$WORKERS" ]; then
    echo "No game-worker instances found."
else
    while read -r name zone; do
        if [ -n "$name" ] && [ -n "$zone" ]; then
            echo "Fetching logs from worker instance: $name ($zone)..."
            
            # Startup logs
            gcloud compute ssh "$name" --zone="$zone" --project="$PROJECT" \
                --command="sudo journalctl -u google-startup-scripts.service --no-pager" > "$OUTPUT_DIR/worker_${name}_startup.log" 2>/dev/null || \
                echo "Warning: Could not fetch startup logs for worker $name"
            
            # Worker container logs
            gcloud compute ssh "$name" --zone="$zone" --project="$PROJECT" \
                --command="sudo docker logs --tail=5000 game-worker" > "$OUTPUT_DIR/worker_${name}_docker.log" 2>/dev/null || \
                echo "Warning: Could not fetch docker logs for game-worker container on $name"
        fi
    done <<< "$WORKERS"
fi

echo "----------------------------------------"
echo "Completed fetching logs!"
echo "Files saved in: $OUTPUT_DIR"
echo "----------------------------------------"
