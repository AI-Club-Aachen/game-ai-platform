# Data source to fetch the latest stable Ubuntu 24.04 LTS image
data "google_compute_image" "ubuntu_2404" {
  family  = "ubuntu-2404-lts-amd64"
  project = "ubuntu-os-cloud"
}

# Static internal IP address allocation for VPC communication
resource "google_compute_address" "backend_internal_ip" {
  name         = "backend-internal-ip"
  subnetwork   = var.subnetwork
  address_type = "INTERNAL"
  region       = var.region
}

# Static external IP address allocation for public access
resource "google_compute_address" "backend_external_ip" {
  name   = "backend-external-ip"
  region = var.region
}

# Compute backend URLs automatically based on domain name or static external IP
locals {
  backend_external_ip = google_compute_address.backend_external_ip.address
  web_host            = var.domain_name != "" ? var.domain_name : local.backend_external_ip
  frontend_url        = var.frontend_url != "" ? var.frontend_url : "https://${local.web_host}"
  api_url             = var.api_url != "" ? var.api_url : "https://${local.web_host}/api/v1"
}

# Compute Engine VM instance for the orchestration backend
resource "google_compute_instance" "backend" {
  name         = "backend"
  machine_type = "e2-standard-8"
  zone         = var.zone

  # VM tags for network policies and firewalls
  tags = ["backend"]

  # Disk configuration using the fetched Ubuntu 24.04 LTS image
  boot_disk {
    initialize_params {
      image = data.google_compute_image.ubuntu_2404.self_link
      size  = 50
      type  = "pd-ssd"
    }
  }

  # Network interface with static internal and static external IP
  network_interface {
    network    = var.network
    subnetwork = var.subnetwork
    network_ip = google_compute_address.backend_internal_ip.address

    access_config {
      nat_ip = google_compute_address.backend_external_ip.address
    }
  }

  # Metadata variables passed as custom attributes to the startup script
  metadata = {
    repo_url                              = var.repo_url
    deploy_ref                            = var.deploy_ref
    postgres_user                         = var.postgres_user
    postgres_password                     = var.postgres_password
    postgres_db                           = var.postgres_db
    jwt_secret_key                        = var.jwt_secret_key
    worker_api_key                        = var.worker_api_key
    redis_password                        = var.redis_password
    smtp_host                             = var.smtp_host
    smtp_port                             = var.smtp_port
    smtp_username                         = var.smtp_username
    smtp_password                         = var.smtp_password
    frontend_url                          = local.frontend_url
    api_url                               = local.api_url
    environment                           = var.environment
    log_level                             = var.log_level
    jwt_algorithm                         = var.jwt_algorithm
    jwt_access_token_expire_hours         = var.jwt_access_token_expire_hours
    api_v1_prefix                         = var.api_v1_prefix
    project_name                          = var.project_name
    smtp_from_address                     = var.smtp_from_address
    smtp_from_name                        = var.smtp_from_name
    smtp_use_tls                          = var.smtp_use_tls
    email_verification_token_expire_hours = var.email_verification_token_expire_hours
    password_reset_token_expire_minutes   = var.password_reset_token_expire_minutes
    bypass_email_verification             = var.bypass_email_verification
    seed_db                               = var.seed_db
    max_turn_time_limit_seconds           = var.max_turn_time_limit_seconds
    db_echo                               = var.db_echo
    domain_name                           = var.domain_name
    certbot_email                         = var.certbot_email

    # Boot script
    startup-script = file("${path.module}/backend-startup.sh")
  }

  # Ensure the VM is automatic restartable
  scheduling {
    automatic_restart   = true
    on_host_maintenance = "MIGRATE"
    preemptible         = false
    provisioning_model  = "STANDARD"
  }
}

# Firewall rule: Public internet access to port 80 and 443
resource "google_compute_firewall" "backend_public" {
  name    = "allow-backend-public"
  network = var.network

  allow {
    protocol = "tcp"
    ports    = ["80", "443"]
  }

  source_ranges = ["0.0.0.0/0"]
  target_tags   = ["backend"]
}

# Firewall rule: VPC-internal traffic from workers to backend API and Redis
resource "google_compute_firewall" "backend_internal" {
  name    = "allow-backend-internal"
  network = var.network

  allow {
    protocol = "tcp"
    ports    = ["8000", "6379"]
  }

  source_tags = [local.name_prefix] # Target worker VM tag ("game-worker")
  target_tags = ["backend"]         # Target backend VM tag
}
