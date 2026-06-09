# Main entrypoint for the Terraform configuration
# This file is used to manage any shared configuration or dependencies.

locals {
  # Common tags and naming prefixes for resources
  name_prefix = "game-worker"
}
