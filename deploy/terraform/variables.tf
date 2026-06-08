variable "project_id" {
  description = "The GCP Project ID where the resources will be deployed."
  type        = string
}

variable "region" {
  description = "The GCP region to deploy the resources in."
  type        = string
}

variable "zone" {
  description = "The GCP zone to deploy the Managed Instance Group and template in."
  type        = string
}

variable "worker_image" {
  description = "The Docker image tag for the worker container."
  type        = string
  default     = "ghcr.io/ai-club-aachen/game-ai-platform/agent-worker:latest"
}

variable "worker_command" {
  description = "The command to run inside the worker container (e.g. 'python agent_builder_worker.py' or 'python match_runner_worker.py')."
  type        = string
  default     = ""
}

variable "backend_url" {
  description = "The URL of the orchestration backend."
  type        = string
}

variable "redis_url" {
  description = "The URL/connection string of the Redis server."
  type        = string
}

variable "worker_token" {
  description = "The secret token for the worker to authenticate with the backend."
  type        = string
  sensitive   = true
}

variable "machine_type" {
  description = "The Compute Engine machine type for the workers."
  type        = string
  default     = "c4-standard-4"
}

variable "network" {
  description = "The name of the VPC network to deploy instances into."
  type        = string
  default     = "default"
}

variable "subnetwork" {
  description = "The name of the VPC subnetwork to deploy instances into."
  type        = string
  default     = "default"
}
