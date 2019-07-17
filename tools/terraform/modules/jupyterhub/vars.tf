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

variable "max_dask_workers" {
  description = "Maximum number of dask worker pods"
}

variable "restrict_lab_nodes" {
  description = "Spawn Lab containers only on nodes with \"jupyterlab: ok\" labels"
}

variable "restrict_dask_nodes" {
  description = "Spawn Dask containers only on nodes with \"dask: ok\" labels"
}

variable "prepuller_experimentals" {
  description = "Number of experimental images to display"
}

variable "prepuller_dailies" {
  description = "Number of daily images to display"
}

variable "prepuller_weeklies" {
  description = "Number of weekly images to display"
}

variable "prepuller_releases" {
  description = "Number of release images to display"
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
  default = 0.5
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

variable "js9_route" {
  description = "Route to JS9 service"
}

variable "api_route" {
  description = "Route to API service"
}

variable "tap_route" {
  description = "Route to TAP service"
}

variable "soda_route" {
  description = "Route to SODA image service"
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

variable "cluster_admin" {
  description = "dummy to sequence cluster admin role creation first"
}

variable "external_instance_url" {
  description = "URL of instance endpoint"
}

variable "external_firefly_url" {
  description = "URL of external Firefly server"
}

variable "external_js9_url" {
  description = "URL of external JS9 server"
}

variable "external_api_url" {
  description = "URL of external API server"
}

variable "external_tap_url" {
  description = "URL of external TAP server"
}

variable "external_soda_url" {
  description = "URL of external SODA server"
}

locals {
  "oauth_callback_url"     = "https://${var.hostname}${var.hub_route}hub/oauth_callback"
  "_keys"                  = "${random_id.crypto_key.hex}"
  "crypto_key"             = "${substr(local._keys,0,32)};${substr(local._keys,32,32)}"
  "configproxy_auth_token" = "${random_id.configproxy_auth_token.hex}"
}
