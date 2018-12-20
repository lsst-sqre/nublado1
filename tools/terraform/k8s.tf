# Get current service account, which should be able to talk to the project
#  we specified

data "google_client_config" "current" {}

# Provider

# https://github.com/sl1pm4t/terraform-provider-kubernetes has the
#  rest of the resources.  Get there eventually....

provider "kubernetes" {
  load_config_file       = false
  host = "${google_container_cluster.jupyter.endpoint}"
  cluster_ca_certificate = "${base64decode(google_container_cluster.jupyter.master_auth.0.cluster_ca_certificate)}"
  token                  = "${data.google_client_config.current.access_token}"
}

module "namespace" {
  source = "./modules/namespace"
  namespace = "${local.kubernetes_cluster_namespace}"
}

module "fileserver" {
  source = "./modules/fileserver"
  quantity = "${var.external_fileserver_ip == "" ? 1 : 0}"
}

module "nfs_pvs" {
  source = "./modules/nfs_pvs"
  namespace = "${local.kubernetes_cluster_namespace}"
  capacity = "${var.volume_size_gigabytes}"
  server_ip = "${var.external_fileserver_ip != "" ? var.external_fileserver_ip : module.fileserver.ip}"
}

module "firefly" {
  source = "./modules/firefly"
  quantity = "${var.firefly_replicas}"
  debug = "${var.debug}"
  namespace = "${local.kubernetes_cluster_namespace}"
  admin_password = "${var.firefly_admin_password}"
  max_jvm_size = "${var.firefly_max_jvm_size}"
  mem_limit = "${var.firefly_container_mem_limit}"
  cpu_limit = "${var.firefly_container_cpu_limit}"
  uid = "${var.firefly_container_uid}"
}

module "jupyterhub" {
  source = "./modules/jupyterhub"
  debug = "${var.debug}"
  hostname = "${var.hostname}"
  namespace = "${local.kubernetes_cluster_namespace}"
  lab_selector_title = "${var.lab_selector_title}"
  oauth_provider = "${var.oauth_provider}"
  allow_dask_spawn = "${var.allow_dask_containers ? "TRUE" : ""}"
  restrict_lab_nodes = "${var.restrict_lab_nodes ? "TRUE" : "" }"
  restrict_dask_nodes = "${var.restrict_dask_nodes ? "TRUE" : "" }"
  repo_host = "${local.lab_repo_host}"
  repo_owner = "${local.lab_repo_owner}"
  repo_name = "${local.lab_repo_name}"
  lab_image = "${var.lab_image}"
  lab_idle_timeout = "${var.lab_idle_timeout}"
  tiny_max_cpu = "${var.tiny_max_cpu}"
  mb_per_cpu = "${var.mb_per_cpu}"
  lab_size_range = "${var.lab_size_range}"
  size_index = "${var.size_index}"
  lab_nodejs_max_mem = "${var.lab_nodejs_max_mem}"
  hub_route = "${var.hub_route}"
  firefly_route = "${var.firefly_route}"
  auto_repo_urls = "${join(",",var.auto_repo_urls)}"
  github_allowed_organizations = "${local.github_allowed_organizations}"
  github_forbidden_organizations = "${local.github_forbidden_organizations}"
  cilogon_allowed_groups = "${local.cilogon_allowed_groups}"
  cilogon_forbidden_groups = "${local.cilogon_forbidden_groups}"
  oauth_client_id = "${var.oauth_client_id}"
  oauth_secret = "${var.oauth_secret}"
  session_db_url = "${var.session_db_url}"
}

module "nginx-ingress" {
  source = "./modules/nginx-ingress"
  k8s_context = "${local.k8s_context}"
  gcloud_account = "${var.gcloud_account}"
}

module "tls" {
  source = "./modules/tls"
  "tls_cert" = "${local.tls_cert}"
  "tls_key" = "${local.tls_key}"
  "tls_root_chain" = "${local.tls_root_chain}"
  "tls_dhparam" = "${local.tls_dhparam}"
}


