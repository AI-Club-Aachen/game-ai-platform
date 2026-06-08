# Dedicated service account for the game worker fleet.
# Following the principle of least privilege, we avoid using the default compute service account.
resource "google_service_account" "worker" {
  account_id   = "${local.name_prefix}-sa"
  display_name = "Game Worker Fleet Service Account"
  description  = "Service account for instances in the game worker Managed Instance Group."
}

# Grant the service account permissions to write logs to Cloud Logging
resource "google_project_iam_member" "logging" {
  project = var.project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${google_service_account.worker.email}"
}

# Grant the service account permissions to write metrics to Cloud Monitoring
resource "google_project_iam_member" "monitoring" {
  project = var.project_id
  role    = "roles/monitoring.metricWriter"
  member  = "serviceAccount:${google_service_account.worker.email}"
}

# Grant the service account reader access to Artifact Registry so it can pull the worker image (if stored there)
resource "google_project_iam_member" "artifact_registry" {
  project = var.project_id
  role    = "roles/artifactregistry.reader"
  member  = "serviceAccount:${google_service_account.worker.email}"
}
