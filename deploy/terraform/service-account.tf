# Dedicated service account for the game worker fleet.
# Following the principle of least privilege, we avoid using the default compute service account.
resource "google_service_account" "worker" {
  account_id   = "${local.name_prefix}-sa"
  display_name = "Game Worker Fleet Service Account"
  description  = "Service account for instances in the game worker Managed Instance Group."
}

# IAM roles required by the game worker instances
locals {
  worker_roles = [
    "roles/logging.logWriter",
    "roles/monitoring.metricWriter",
    "roles/artifactregistry.reader",
  ]
}

# Grant the necessary IAM permissions to the worker service account
resource "google_project_iam_member" "worker_roles" {
  for_each = toset(local.worker_roles)

  project = var.project_id
  role    = each.value
  member  = "serviceAccount:${google_service_account.worker.email}"
}

