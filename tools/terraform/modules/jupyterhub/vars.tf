variable "debug" {
  description = "enable debug logging"
}

variable "namespace" {
  description = "k8s namespace in which to run JupyterHub"
}

variable "lab_selector_title" {
  description = "Title for spawner selector page"
}

variable "oauth_provider" {
  description = "One of 'github' or 'cilogon'"
}

variable "allow_dask_spawn" {
  description = "Allow users to spawn dask workers"
}

variable "restrict_lab_nodes" {
  description = "Spawn Lab containers only on nodes with \"jupyterlab: ok\" labels"
}

variable "restrict_dask_nodes" {
  description = "Spawn Dask containers only on nodes with \"dask: ok\" labels"
}

variable "repo_host" {
  description = "Docker repository host for Lab images"
}

variable "repo_owner" {
  description = "Owner of Lab images"
}

variable "repo_name" {
  description = "Lab image name"
}

variable "lab_image" {
  description = "Single image for presenting"
}

variable "lab_idle_timeout" {
  description = "Time in seconds before idle container is reaped"
}

variable "tiny_max_cpu" {
  default=0.5
}

variable "mb_per_cpu" {
  description = "Ratio of megabytes to cores in containers"
}

variable "lab_size_range" {
  description = "Ratio of maximum to initially-requested container resources"
}

variable "size_index" {
  description = "Index of default size (usually range of 0-3)"
}

variable "lab_nodejs_max_mem" {
  description = "Maximum size in megabytes that node.js can consume"
}

variable "auto_repo_urls" {
  description = "Repositories to be checked out automatically at lab start"
}

variable "hub_route" {
  description = "Route to JupyterHub"
}

variable "firefly_route" {
  description = "Route to firefly"
}

variable "github_allowed_organizations" {
  description = "List of GitHub organizations allowed to use Jupyter"
}

variable "cilogon_allowed_groups" {
  description = "List of CILogon groups allowed to use Jupyter"
}

variable "github_forbidden_organizations" {
  description = "List of GitHub organizations forbidden from using Jupyter"
}

variable "cilogon_forbidden_groups" {
  description = "List of CILogon groups forbidden from using Jupyter"
}

variable "oauth_client_id" {
  description = "Client ID to use for OAuth authentication"
}

variable "oauth_secret" {
  description = "OAuth secret for authentication"
}

variable "hostname" {
  description = "FQDN of Jupyter endpoint"
}

variable "session_db_url" {
  description = "session storage location; any SQLAlchemy URL will work"
}

locals {
  "oauth_callback_url" = "https://${var.hostname}${var.hub_route}hub/oauth_callback"
  "_keys" = "${random_id.crypto_key.hex}"
  "crypto_key" = "${substr(local._keys,0,32)};${substr(local._keys,32,32)}"
}
  
