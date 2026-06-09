# GCP Game Platform Infrastructure Deployment

This directory contains the Terraform configuration and instance startup scripts to provision the platform infrastructure on Google Cloud Platform (GCP).

## Architecture Overview

The infrastructure consists of two main components running in the same VPC:

1. **Backend VM**:
   - A single Compute Engine VM (`e2-standard-4`, 50GB SSD, Ubuntu 24.04 LTS) tagged `backend`.
   - Attaches a static internal IP (`backend-internal-ip`) for private communication with workers, and a static external IP (`backend-external-ip`) for public internet access.
   - Runs the services via Docker Compose: `frontend`, `backend` (FastAPI), `postgres`, `redis`, and **`nginx`** as a reverse proxy.
   - Ports `80` and `443` (HTTPS) are exposed publicly, with Nginx redirecting port 80 to 443.
   - Ports `8000` (FastAPI) and `6379` (Redis) are exposed internally only for VPC workers.
   - A self-signed SSL certificate is generated automatically during startup to secure connections immediately.

2. **Worker Fleet (MIG)**:
   - A zonal Managed Instance Group (MIG) housing the worker VM instances running Container-Optimized OS (COS).
   - Worker instances run a standalone Docker container (`agent-worker`) tagged `game-worker`.
   - Workers query the GCE metadata server to dynamically retrieve connection strings pointing to the backend VM's static internal IP (`http://<backend_internal_ip>:8000/api/v1` and `redis://<backend_internal_ip>:6379`).

```text
       Internet
          │
          ▼ (Ports: 80, 443)
┌─────────────────────────────────┐
│           Backend VM            │
│ ├─ nginx    (reverse proxy)     │
│ ├─ frontend (port 3000)         │
│ ├─ backend  (port 8000) ◄─────┐ │
│ ├─ redis    (port 6379) ◄───┐ │ │
│ └─ postgres (port 5432)     │ │ │
└─────────────────────────────┼─┼─┘
                              │ │ (Ports: 8000, 6379 via VPC internal)
┌─────────────────────────────┼─┼─┐
│         Worker MIG          │ │ │
│ └─ game-worker instances ───┴─┴─┘
└─────────────────────────────────┘
```

---

## Directory Structure

```text
deploy/
├── terraform/
│   ├── main.tf              # Shared configurations and local variables
│   ├── variables.tf         # Input variables and defaults
│   ├── outputs.tf           # Exported output values (MIG, Backend IPs, etc.)
│   ├── providers.tf         # Google Cloud provider configurations
│   ├── service-account.tf   # Dedicated least-privilege IAM service account
│   ├── worker-template.tf   # Compute Engine Instance Template for workers
│   ├── worker-mig.tf        # Zonal Managed Instance Group for workers
│   ├── worker-startup.sh    # COS boot script for worker instances
│   ├── backend-vm.tf        # Compute Engine VM configuration for backend stack
│   └── backend-startup.sh   # Bash boot script for backend VM
│
└── README.md                # This setup and operation guide
```

---

## Configuration Variables

Create a `terraform.tfvars` file inside `deploy/terraform/` to configure the deployment:

### Required & Key Variables

| Variable | Type | Description | Default / Example |
| :--- | :--- | :--- | :--- |
| `project_id` | `string` | The GCP Project ID where resources will be deployed. | *(Required)* |
| `region` | `string` | The GCP region (e.g. `europe-west3`). | *(Required)* |
| `zone` | `string` | The GCP zone (e.g. `europe-west3-a`). | *(Required)* |
| `postgres_password` | `string` | Password for the PostgreSQL container (sensitive). | *(Required)* |
| `jwt_secret_key` | `string` | Secret key used to sign JWT access tokens (sensitive). | *(Required)* |
| `worker_api_key` | `string` | Authentication token shared between backend and workers (sensitive). | *(Required)* |
| `smtp_password` | `string` | Password for SMTP email verification service (sensitive). | *(Required)* |
| `repo_url` | `string` | Git repository containing the docker compose stack to clone on VM. | `"https://github.com/AI-Club-Aachen/game-ai-platform.git"` |
| `worker_image` | `string` | Docker image path for the worker container. | `"ghcr.io/ai-club-aachen/game-ai-platform/agent-worker:latest"` |
| `worker_command` | `string` | Optional command to override the worker container's entrypoint. | `""` |
| `network` | `string` | The VPC network name. | `"default"` |
| `subnetwork` | `string` | The VPC subnet name. | `"default"` |

*Note: Additional parameters for SMTP hosts, token lifetimes, and environment settings are defined with sensible defaults inside `variables.tf` and can be overridden as needed.*

### Example `terraform.tfvars`

```hcl
project_id        = "my-gcp-project-123"
region            = "europe-west3"
zone              = "europe-west3-a"
worker_image      = "ghcr.io/ai-club-aachen/game-ai-platform/agent-worker:latest"

postgres_password = "a-very-strong-postgres-password"
jwt_secret_key    = "openssl-generated-hex-jwt-secret-key"
worker_api_key    = "openssl-generated-hex-worker-api-key"
smtp_password     = "my-smtp-password-key"
```

---

## Deployment Instructions

### Prerequisites
- Install [Terraform CLI](https://developer.hashicorp.com/terraform/downloads) (v1.3.0+).
- Install [Google Cloud CLI](https://cloud.google.com/sdk/docs/install).

### Step 1: GCP Authentication
Log in to GCP and set up Application Default Credentials:
```bash
gcloud auth login
gcloud auth application-default login
gcloud config set project <your-project-id>
```

### Step 2: Initialize Terraform
Navigate to the Terraform directory and initialize the state and provider:
```bash
cd deploy/terraform
terraform init
```

### Step 3: Plan and Apply
Preview the resources to be created:
```bash
terraform plan
```
If the plan looks correct, apply the configuration:
```bash
terraform apply
```

### Step 4: Accessing the Outputs
After a successful apply, Terraform outputs the connection details for the backend:
- `backend_external_ip`: The public IP to access the frontend (port 80) and API (port 8000).
- `backend_internal_ip`: The private IP used for worker communications.
- `backend_instance_name`: The VM name of the backend.

---

## Troubleshooting & Verification

### 1. Backend VM Configuration
To verify that the backend services launched successfully, SSH into the backend VM:
```bash
gcloud compute ssh backend --zone=<zone>
```
Inspect the startup script logs:
```bash
sudo tail -f /var/log/backend-startup.log
```
Check the status of the Docker Compose services:
```bash
cd /opt/gameai
sudo docker compose ps
sudo docker compose logs -f backend
```

### 2. Worker Fleet Configuration
To verify that the workers are connecting to the backend VM over the VPC network:
```bash
gcloud compute ssh <worker-instance-name> --zone=<zone>
```
Inspect the worker's startup progress:
```bash
sudo journalctl -u google-startup-scripts.service -f
```
Verify the worker container is running:
```bash
sudo docker ps
sudo docker logs game-worker -f
```
