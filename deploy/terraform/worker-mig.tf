# Managed Instance Group (MIG) for the game workers
resource "google_compute_instance_group_manager" "worker_mig" {
  name               = "${local.name_prefix}-mig"
  base_instance_name = local.name_prefix
  zone               = var.zone

  # References the instance template defined in worker-template.tf
  version {
    name              = "primary"
    instance_template = google_compute_instance_template.worker.id
  }

  # Initial target size is 0. Scaling is controlled externally by the backend orchestrator.
  target_size = 0

  # Configuration for updates to VM instances in the MIG
  update_policy {
    type                  = "PROACTIVE"
    minimal_action        = "REPLACE"
    max_surge_fixed       = 3
    max_unavailable_fixed = 0
  }

  lifecycle {
    # Crucial: Ignore changes to target_size in future runs.
    # The external backend will scale this group dynamically, and we do not want
    # Terraform to fight the backend by resetting the size to 0 during 'terraform apply'.
    ignore_changes = [
      target_size
    ]
  }
}
