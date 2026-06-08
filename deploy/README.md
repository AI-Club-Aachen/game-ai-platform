# GCP Game Worker Fleet Deployment

This directory contains the Terraform configuration and instance startup script to provision a manually-scaled worker fleet on Google Cloud Platform (GCP).

The instances run on **Container-Optimized OS (COS)**, hosting a Docker container pulled from your container registry. The configuration (backend, Redis, credentials, image) is injected via GCE instance metadata, allowing the startup script to run completely hands-off.

---

## Directory Structure

```text
deploy/
├── terraform/
│   ├── main.tf              # Shared configurations and local variables
│   ├── variables.tf         # Input variables and defaults
│   ├── outputs.tf           # Exported output values (MIG URI, Service Account, etc.)
│   ├── providers.tf         # Google Cloud provider configurations
│   ├── service-account.tf   # Dedicated least-privilege IAM service account
│   ├── worker-template.tf   # Compute Engine Instance Template
│   ├── mig.tf               # Zonal Managed Instance Group
│   └── startup.sh           # COS boot script (validates metadata & starts Docker container)
│
└── README.md                # This setup and operation guide
```

---

## Architecture Overview

1. **Zonal Managed Instance Group (MIG)**: Houses the worker VM instances. The initial fleet size is set to `0`. Fleet scaling is controlled externally by the backend application or scripts modifying the MIG's target size.
2. **Container-Optimized OS (COS)**: A minimal, security-hardened Linux image maintained by Google that has Docker pre-installed.
3. **Dedicated Service Account**: The instances run as `game-worker-sa`, which has permissions to write logs and metrics to GCP, and read-access to GCP Artifact Registry to pull the docker image.
4. **No Spot VMs**: Standard VMs (`c4-standard-4` by default) are used to ensure that game workers are not preempted during active workloads.

---

## Configuration Variables

Create a `terraform.tfvars` file inside `deploy/terraform/` to configure the deployment:

| Variable | Type | Description | Default |
| :--- | :--- | :--- | :--- |
| `project_id` | `string` | The GCP Project ID where resources will be deployed. | *(Required)* |
| `region` | `string` | The GCP region (e.g. `us-central1`). | *(Required)* |
| `zone` | `string` | The GCP zone (e.g. `us-central1-a`). | *(Required)* |
| `worker_image` | `string` | Docker image path for the worker container (e.g. `us-central1-docker.pkg.dev/my-project/my-repo/worker:v1`). | *(Required)* |
| `backend_url` | `string` | The connection URL for the orchestrator backend. | *(Required)* |
| `redis_url` | `string` | The Redis connection URL (e.g. `redis://10.0.0.3:6379`). | *(Required)* |
| `worker_token` | `string` | Secret authentication token used by the worker (marked sensitive). | *(Required)* |
| `machine_type` | `string` | Compute Engine VM Machine Type. | `"c4-standard-4"` |
| `network` | `string` | The VPC network name. | `"default"` |
| `subnetwork` | `string` | The VPC subnet name. | `"default"` |

### Example `terraform.tfvars`

```hcl
project_id   = "my-gcp-project-123"
region       = "us-central1"
zone         = "us-central1-a"
worker_image = "us-central1-docker.pkg.dev/my-gcp-project-123/game-registry/worker:latest"
backend_url  = "https://api.mygameplatform.com"
redis_url    = "redis://10.128.0.5:6379"
worker_token = "super-secret-auth-token-xyz"
```

---

## Deployment Instructions

### Prerequisites
- Install [Terraform CLI](https://developer.hashicorp.com/terraform/downloads) (v1.3.0+).
- Install [Google Cloud CLI](https://cloud.google.com/sdk/docs/install).

### Step 1: GCP Authentication
Log in to GCP and set up Application Default Credentials so Terraform can authenticate:
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

---

## Scaling the Fleet

Because we configure the MIG with:
```hcl
lifecycle {
  ignore_changes = [target_size]
}
```
Terraform will **not** scale the fleet back to `0` on subsequent runs of `terraform apply`.

### Manual Scaling (via gcloud)
You can manually resize the group using the gcloud command line tool:
```bash
gcloud compute instance-groups managed resize game-worker-mig \
    --size=5 \
    --zone=us-central1-a
```

### Automated Scaling (via API)
Your orchestrator backend can call the [Google Compute Engine REST API](https://cloud.google.com/compute/docs/reference/rest/v1/instanceGroupManagers/resize) directly to resize the group:
```http
POST https://compute.googleapis.com/compute/v1/projects/{project}/zones/{zone}/instanceGroupManagers/game-worker-mig/resize?size=10
Authorization: Bearer <oauth2-token>
```

---

## Troubleshooting & Verification

Once instances are running, they execute `startup.sh` automatically.

### 1. View Startup Script Logs
Connect to an instance via SSH:
```bash
gcloud compute ssh <instance-name> --zone=<zone>
```
To view the output of the instance's startup script execution:
```bash
sudo journalctl -u google-startup-scripts.service -f
```

### 2. View Worker Container Logs
To inspect the Docker container logs directly:
```bash
sudo docker ps
sudo docker logs game-worker -f
```

### 3. Fail-Fast Verification
If you miss any metadata settings during VM creation, the startup script will exit immediately. You will see a message in the system log like:
`CRITICAL ERROR: The following required metadata attributes are missing: backend_url worker_token`
This prevents launching misconfigured workers that cannot connect to the backend.
