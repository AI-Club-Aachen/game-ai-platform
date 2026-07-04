#!/usr/bin/env bash
# backup_postgres.sh - Backs up Postgres data from the running database container on the backend VM.

set -euo pipefail

usage() {
    echo "Usage: $0 -p <project-id> -z <zone> -o <local-output-file> [-m <logical|physical>]"
    echo "  -p  GCP Project ID (required)"
    echo "  -z  GCP Zone (required)"
    echo "  -o  Local path for the output file (required)"
    echo "  -m  Backup mode: 'logical' or 'physical' (default: 'logical')"
    echo "      logical  - Run online pg_dump (zero downtime, outputs SQL)"
    echo "      physical - Stop containers, create tarball of Docker volume, restart containers"
    exit 1
}

PROJECT=""
ZONE=""
OUTPUT_FILE=""
MODE="logical"

while getopts "p:z:o:m:h" opt; do
    case "$opt" in
        p) PROJECT=$OPTARG ;;
        z) ZONE=$OPTARG ;;
        o) OUTPUT_FILE=$OPTARG ;;
        m) MODE=$OPTARG ;;
        h|*) usage ;;
    esac
done

if [ -z "$PROJECT" ] || [ -z "$ZONE" ] || [ -z "$OUTPUT_FILE" ]; then
    echo "Error: Missing required arguments."
    usage
fi

if [ "$MODE" != "logical" ] && [ "$MODE" != "physical" ]; then
    echo "Error: Invalid backup mode '$MODE'."
    usage
fi

# Make sure parent directory of output file exists
mkdir -p "$(dirname "$OUTPUT_FILE")"

if [ "$MODE" == "logical" ]; then
    echo "Starting LOGICAL backup (zero downtime, using pg_dump)..."
    # Execute pg_dump inside DB container and pipe output directly to local file
    gcloud compute ssh backend --zone="$ZONE" --project="$PROJECT" \
        --command="cd /opt/gameai && sudo docker compose exec -T db pg_dump -U \${POSTGRES_USER:-postgres} -d \${POSTGRES_DB:-gameai}" > "$OUTPUT_FILE"
    
    echo "Logical backup completed successfully. Saved to: $OUTPUT_FILE"
else
    echo "Starting PHYSICAL backup (requires temporary container stop)..."
    
    # 1. Stop backend services to freeze DB writes safely
    echo "Stopping backend and db containers on the VM..."
    gcloud compute ssh backend --zone="$ZONE" --project="$PROJECT" \
        --command="cd /opt/gameai && sudo docker compose stop backend db"
    
    # 2. Archive postgres_data volume into a temporary tarball
    echo "Creating archive of gameai_postgres_data volume on the VM..."
    gcloud compute ssh backend --zone="$ZONE" --project="$PROJECT" \
        --command="sudo docker run --rm -v gameai_postgres_data:/volume -v /opt/gameai:/backup alpine tar -czf /backup/postgres_backup.tar.gz -C /volume ."
    
    # 3. Restart backend services immediately
    echo "Restarting backend and db containers on the VM..."
    gcloud compute ssh backend --zone="$ZONE" --project="$PROJECT" \
        --command="cd /opt/gameai && sudo docker compose start db backend"
    
    # 4. Copy the tarball from backend VM to the local machine
    echo "Downloading database tarball to local machine..."
    gcloud compute scp backend:/opt/gameai/postgres_backup.tar.gz "$OUTPUT_FILE" --zone="$ZONE" --project="$PROJECT"
    
    # 5. Clean up temporary tarball on the backend VM
    echo "Cleaning up temporary archive on the VM..."
    gcloud compute ssh backend --zone="$ZONE" --project="$PROJECT" \
        --command="sudo rm -f /opt/gameai/postgres_backup.tar.gz"
    
    echo "Physical backup completed successfully. Saved to: $OUTPUT_FILE"
fi
