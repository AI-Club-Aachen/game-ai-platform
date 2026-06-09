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
  default     = "python match_runner_worker.py"
}

variable "worker_api_key" {
  description = "The secret API key for workers and backend validation."
  type        = string
  sensitive   = true
}

variable "machine_type" {
  description = "The Compute Engine machine type for the workers."
  type        = string
  default     = "e2-micro"
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

variable "repo_url" {
  description = "The URL of the Git repository to clone on the backend VM."
  type        = string
  default     = "https://github.com/AI-Club-Aachen/game-ai-platform.git"
}

variable "postgres_user" {
  description = "The database user name."
  type        = string
  default     = "postgres"
}

variable "postgres_password" {
  description = "The database user password."
  type        = string
  sensitive   = true
}

variable "postgres_db" {
  description = "The database name."
  type        = string
  default     = "gameai"
}

variable "jwt_secret_key" {
  description = "Secret key used to sign JSON Web Tokens."
  type        = string
  sensitive   = true
}

variable "smtp_host" {
  description = "The hostname of the SMTP server."
  type        = string
  default     = "smtp.gmail.com"
}

variable "smtp_port" {
  description = "The port of the SMTP server."
  type        = string
  default     = "587"
}

variable "smtp_username" {
  description = "The SMTP server username."
  type        = string
  default     = "smtp_user"
}

variable "smtp_password" {
  description = "The SMTP server password."
  type        = string
  sensitive   = true
}

variable "frontend_url" {
  description = "Custom public URL of the frontend (if empty, defaults to external IP)."
  type        = string
  default     = ""
}

variable "api_url" {
  description = "Custom public URL of the backend API (if empty, defaults to external IP)."
  type        = string
  default     = ""
}

variable "environment" {
  description = "Deployment environment (development, staging, production)."
  type        = string
  default     = "production"
}

variable "log_level" {
  description = "Log level for the application."
  type        = string
  default     = "info"
}

variable "jwt_algorithm" {
  description = "The cryptographic algorithm for signing JWT tokens."
  type        = string
  default     = "HS256"
}

variable "jwt_access_token_expire_hours" {
  description = "Duration in hours before JWT tokens expire."
  type        = string
  default     = "24"
}

variable "api_v1_prefix" {
  description = "Routing prefix for the API."
  type        = string
  default     = "/api/v1"
}

variable "project_name" {
  description = "The display name of the project."
  type        = string
  default     = "AI Game Competition Platform"
}

variable "smtp_from_address" {
  description = "The sender email address for system emails."
  type        = string
  default     = "noreply@your-domain.com"
}

variable "smtp_from_name" {
  description = "The sender name for system emails."
  type        = string
  default     = "AI Game Platform"
}

variable "smtp_use_tls" {
  description = "Use TLS connection for SMTP (true/false)."
  type        = string
  default     = "true"
}

variable "email_verification_token_expire_hours" {
  description = "Hours before verification token expires."
  type        = string
  default     = "24"
}

variable "password_reset_token_expire_minutes" {
  description = "Minutes before password reset token expires."
  type        = string
  default     = "60"
}

variable "bypass_email_verification" {
  description = "Bypass email verification (true/false)."
  type        = string
  default     = "false"
}

variable "seed_db" {
  description = "Seed the database with demo data (true/false)."
  type        = string
  default     = "false"
}

variable "max_turn_time_limit_seconds" {
  description = "Max turn time limit in seconds for matches."
  type        = string
  default     = "120"
}

variable "db_echo" {
  description = "Enable SQLAlchemy echo log (true/false)."
  type        = string
  default     = "false"
}
