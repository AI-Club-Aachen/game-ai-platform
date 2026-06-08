# Data source to fetch the latest stable Container-Optimized OS (COS) image
data "google_compute_image" "cos_stable" {
  family  = "cos-stable"
  project = "cos-cloud"
}

# Instance Template for the worker instances
resource "google_compute_instance_template" "worker" {
  name_prefix  = "${local.name_prefix}-template-"
  description  = "Template for Game Worker instances running Container-Optimized OS."
  machine_type = var.machine_type
  region       = var.region

  # Disk configuration using the fetched COS image
  disk {
    source_image = data.google_compute_image.cos_stable.self_link
    auto_delete  = true
    boot         = true
    type         = "pd-balanced"
    disk_size_gb = 30 # standard default size for worker nodes
  }

  # Network configuration
  network_interface {
    network    = var.network
    subnetwork = var.subnetwork

    # Allocates a temporary public IP to the instance so it can fetch external repositories and packages.
    # In a fully private VPC, this can be omitted if a Cloud NAT is configured.
    access_config {}
  }

  # Service Account and Scopes
  service_account {
    email  = google_service_account.worker.email
    scopes = ["https://www.googleapis.com/auth/cloud-platform"]
  }

  # Metadata variables read by the startup script
  metadata = {
    backend_url    = var.backend_url
    redis_url      = var.redis_url
    worker_token   = var.worker_token
    worker_image   = var.worker_image
    startup-script = file("${path.module}/startup.sh")
  }

  # VM tags for network policies and firewalls
  tags = [local.name_prefix]

  # Ensure instances are standard VMs (Strictly No Spot/Preemptible VMs)
  scheduling {
    automatic_restart   = true
    on_host_maintenance = "MIGRATE"
    preemptible         = false
    provisioning_model  = "STANDARD"
  }

  lifecycle {
    create_before_destroy = true
  }
}
