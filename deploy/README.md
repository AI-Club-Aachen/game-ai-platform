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
| `smtp_host` | `string` | SMTP server hostname. The built-in default is a **placeholder** — email verification fails unless this is set. | *(Required)* |
| `smtp_port` | `string` | SMTP server port. Use `465` for implicit TLS (SMTPS) or `587` for STARTTLS. Must match `smtp_use_tls`. | *(Required)* |
| `smtp_username` | `string` | SMTP login user (usually the full sender email). The built-in default is a placeholder. | *(Required)* |
| `smtp_from_address` | `string` | Sender address for system emails. The built-in default is a placeholder; should match the authenticated mailbox. | *(Required)* |
| `smtp_use_tls` | `string` | `"true"` = implicit TLS (pair with port `465`); `"false"` = STARTTLS (pair with port `587`). | *(Required)* |
| `redis_password` | `string` | Password for Redis (sensitive). Required so Redis is never passwordless (M-7). | *(Required)* |
| `deploy_ref` | `string` | Immutable git ref (release tag or commit SHA) the backend checks out on boot. Defaults to `main`; pin it for reproducible deploys. | *(Required)* |
| `repo_url` | `string` | Git repository containing the docker compose stack to clone on VM. | `"https://github.com/AI-Club-Aachen/game-ai-platform.git"` |
| `worker_image` | `string` | Docker image path for the worker container. | `"ghcr.io/ai-club-aachen/game-ai-platform/agent-worker:latest"` |
| `worker_command` | `string` | The command to run inside the worker container (e.g. 'python agent_builder_worker.py' or 'python match_runner_worker.py'). | `"python match_runner_worker.py"` |
| `network` | `string` | The VPC network name. | `"default"` |
| `subnetwork` | `string` | The VPC subnet name. | `"default"` |
| `domain_name` | `string` | The registered domain name pointing to the VM external IP address. Leave empty to use self-signed certificates. | `""` |
| `certbot_email` | `string` | The email address for Let's Encrypt renewal warnings. Required if `domain_name` is set. | `""` |
| `frontend_url` | `string` | Custom public URL of the frontend (defaults to external IP if empty). | `""` |
| `api_url` | `string` | Custom public URL of the backend API (defaults to external IP if empty). | `""` |

*Note: The SMTP variables above ship with **placeholder defaults** in `variables.tf` (e.g. `smtp_username = "smtp_user"`, `smtp_from_address = "noreply@your-domain.com"`). They will pass validation but silently fail to send mail, so they must be set to real values. Other parameters (token lifetimes, `environment`, etc.) have sensible defaults and can be overridden as needed.*

> ⚠️ Changing any of these values only takes effect on a **fresh VM boot**. The backend `startup-script` runs once at boot and bakes them into the VM's `.env`. A plain `terraform apply` updates instance metadata in place but does **not** re-run startup — use `terraform apply -replace="google_compute_instance.backend"` (see [Common Operations](#common-operations)).

### Example `terraform.tfvars`

```hcl
project_id        = "my-gcp-project-123"
region            = "europe-west3"
zone              = "europe-west3-a"
worker_image      = "ghcr.io/ai-club-aachen/game-ai-platform/agent-worker:latest"

deploy_ref        = "v1.0.0"   # release tag or commit SHA; avoid moving branches

postgres_password = "a-very-strong-postgres-password"
jwt_secret_key    = "openssl-generated-hex-jwt-secret-key"
worker_api_key    = "openssl-generated-hex-worker-api-key"
redis_password    = "openssl-generated-hex-redis-password"

# SMTP — all required for email verification (defaults are placeholders)
smtp_host         = "mail.example.com"
smtp_port         = "465"
smtp_use_tls      = "true"
smtp_username     = "noreply@example.com"
smtp_from_address = "noreply@example.com"
smtp_password     = "my-smtp-password-key"

# Optional: Custom domain configuration (Uncomment to enable Let's Encrypt SSL).
# Note: certbot also requests a SAN for the `api.` subdomain, so point both the
# apex and `api.<domain>` A records at the backend external IP.
# Do NOT add a trailing slash to frontend_url — it becomes the CORS origin and a
# browser Origin never has one (mismatch breaks CORS).
# domain_name   = "game.example.com"
# certbot_email = "admin@example.com"
# frontend_url  = "https://game.example.com"
# api_url       = "https://api.game.example.com/api/v1"
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

## Common Operations

All `terraform` commands run from `deploy/terraform/`. Replace `<zone>` (e.g. `europe-west3-a`) and `<project-id>` with your values.

### Start / deploy the backend
First deploy, or apply infra changes that don't require re-running the VM boot script:
```bash
terraform apply
```

### Replace the backend (re-run the startup script)
Required whenever you change `deploy_ref`, `domain_name`, SMTP, Redis, or any other value baked into the VM's `.env` at boot. A plain `apply` only updates metadata in place and will **not** re-run startup.
```bash
terraform apply -replace="google_compute_instance.backend"
```
Confirm the plan says the instance **will be replaced** (`1 to destroy`). ⚠️ This recreates the VM on a fresh disk, so **PostgreSQL data is wiped**. Workers in the MIG are unaffected.

### Start / scale up workers
Workers run in a Managed Instance Group that starts at size 0. Scale it to the number of workers you want (they boot, pull the image, and reconnect over the VPC automatically — no backend restart needed):
```bash
gcloud compute instance-groups managed resize game-worker-mig \
  --size=4 --zone=<zone> --project=<project-id>
```

### Stop / scale down workers
Set the size to 0 to delete all worker VMs (stops billing for them):
```bash
gcloud compute instance-groups managed resize game-worker-mig \
  --size=0 --zone=<zone> --project=<project-id>
```
List current workers:
```bash
gcloud compute instances list --filter="name~game-worker" \
  --zones=<zone> --project=<project-id>
```
*Terraform does not fight these manual sizes — the MIG's `target_size` has `ignore_changes` set.*

### Promote a user to admin
Roles are `GUEST`, `USER`, `ADMIN` (the Postgres `userrole` enum stores the uppercase names — lowercase values are rejected). The user must have registered first, and the first admin must be set directly in the database (the role-change API requires an existing admin). Run the update on the VM in a single command (the `-T` disables Docker's TTY allocation, required for a non-interactive remote command):
```bash
gcloud compute ssh backend --zone=<zone> --project=<project-id> \
  --command="cd /opt/gameai && sudo docker compose exec -T db psql -U postgres -d gameai -c \"UPDATE users SET role='ADMIN' WHERE email='someone@example.com';\""
```
`psql` prints `UPDATE 1` on success (`UPDATE 0` means no user has that email).

*Adjust `-U`/`-d` if you overrode `postgres_user` / `postgres_db`. Once one admin exists, further role changes can be made via `PATCH /api/v1/users/{user_id}/role`.*

---

## Troubleshooting & Verification

### 1. Backend VM Configuration
Each check runs as a single command from your machine (no interactive session needed).

Inspect the startup script log:
```bash
gcloud compute ssh backend --zone=<zone> --project=<project-id> \
  --command="sudo tail -n 100 /var/log/backend-startup.log"
```
Check the status of the Docker Compose services:
```bash
gcloud compute ssh backend --zone=<zone> --project=<project-id> \
  --command="cd /opt/gameai && sudo docker compose ps"
```
Tail the backend logs (e.g. to debug SMTP/email):
```bash
gcloud compute ssh backend --zone=<zone> --project=<project-id> \
  --command="cd /opt/gameai && sudo docker compose logs --tail=200 backend"
```
*To open an interactive shell instead, run `gcloud compute ssh backend --zone=<zone> --project=<project-id>` on its own, then run the inner commands at the VM prompt.*

To re-run the startup script (e.g. after changing SMTP, domain, or `deploy_ref`), replace the backend VM — note this wipes all data. See [Replace the backend](#replace-the-backend-re-run-the-startup-script) under Common Operations.

### 2. Worker Fleet Configuration
Find a worker instance name first:
```bash
gcloud compute instances list --filter="name~game-worker" \
  --zones=<zone> --project=<project-id>
```
Inspect the worker's startup progress:
```bash
gcloud compute ssh <worker-instance-name> --zone=<zone> --project=<project-id> \
  --command="sudo journalctl -u google-startup-scripts.service --no-pager | tail -n 100"
```
Verify the worker container is running and tail its logs:
```bash
gcloud compute ssh <worker-instance-name> --zone=<zone> --project=<project-id> \
  --command="sudo docker ps && sudo docker logs --tail=100 game-worker"
```
