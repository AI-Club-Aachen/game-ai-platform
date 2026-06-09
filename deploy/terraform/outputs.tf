output "mig_name" {
  description = "The name of the Managed Instance Group."
  value       = google_compute_instance_group_manager.worker_mig.name
}

output "mig_self_link" {
  description = "The self link of the Managed Instance Group manager."
  value       = google_compute_instance_group_manager.worker_mig.self_link
}

output "mig_instance_group" {
  description = "The URI of the instance group resource. Use this for resizing the group via GCP API."
  value       = google_compute_instance_group_manager.worker_mig.instance_group
}

output "service_account_email" {
  description = "The email of the dedicated worker service account."
  value       = google_service_account.worker.email
}

output "instance_template_name" {
  description = "The name of the instance template used by the MIG."
  value       = google_compute_instance_template.worker.name
}

output "backend_internal_ip" {
  description = "The static internal IP address of the backend VM."
  value       = google_compute_address.backend_internal_ip.address
}

output "backend_external_ip" {
  description = "The static external IP address of the backend VM."
  value       = google_compute_address.backend_external_ip.address
}

output "backend_instance_name" {
  description = "The name of the backend VM instance."
  value       = google_compute_instance.backend.name
}
