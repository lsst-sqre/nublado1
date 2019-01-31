# Get current service account, which should be able to talk to the project
#  we specified

data "google_client_config" "current" {}

# Provider

# https://github.com/sl1pm4t/terraform-provider-kubernetes has the
#  rest of the resources.  That's what "1.3.0-custom" is

provider "kubernetes" {
  version                = "1.3.0-custom"
  load_config_file       = false
  host                   = "${google_container_cluster.jupyter.endpoint}"
  cluster_ca_certificate = "${base64decode(google_container_cluster.jupyter.master_auth.0.cluster_ca_certificate)}"
  token                  = "${data.google_client_config.current.access_token}"
}

module "cluster_admin" {
  source           = "./modules/cluster_admin"
  "gcloud_account" = "${var.gcloud_account}"
}

resource "kubernetes_namespace" "hub" {
  metadata {
    name = "${local.kubernetes_cluster_namespace}"
  }
}

module "tls" {
  source           = "./modules/tls"
  namespace        = "${kubernetes_namespace.hub.metadata.0.name}"
  "tls_cert"       = "${local.tls_cert}"
  "tls_key"        = "${local.tls_key}"
  "tls_root_chain" = "${local.tls_root_chain}"
  "tls_dhparam"    = "${local.tls_dhparam}"
}

module "fileserver" {
  source      = "./modules/fileserver"
  ip          = "${var.external_fileserver_ip}"
  volume_size = "${var.volume_size_gigabytes}"
  namespace   = "${kubernetes_namespace.hub.metadata.0.name}"
}

module "nfs_pvs" {
  source    = "./modules/nfs_pvs"
  namespace = "${kubernetes_namespace.hub.metadata.0.name}"
  capacity  = "${var.volume_size_gigabytes}"
  server_ip = "${module.fileserver.ip}"
}

module "landing_page" {
  source    = "./modules/landing_page"
  namespace = "${kubernetes_namespace.hub.metadata.0.name}"
  hostname  = "${var.hostname}"
}

module "prepuller" {
  source              = "./modules/prepuller"
  debug               = "${var.debug}"
  repo                = "${var.prepuller_repo}"
  owner               = "${var.prepuller_owner}"
  image_list          = "${var.prepuller_image_list}"
  no_scan             = "${var.prepuller_no_scan}"
  image_name          = "${var.prepuller_image_name}"
  dailies             = "${var.prepuller_dailies}"
  weeklies            = "${var.prepuller_weeklies}"
  releases            = "${var.prepuller_releases}"
  insecure            = "${var.prepuller_insecure}"
  port                = "${var.prepuller_port}"
  sort_field          = "${var.prepuller_sort_field}"
  command             = "${var.prepuller_command}"
  prepuller_namespace = "${var.prepuller_namespace == "" ? kubernetes_namespace.hub.metadata.0.name : var.prepuller_namespace}"
}

module "firefly" {
  source         = "./modules/firefly"
  quantity       = "${var.firefly_replicas}"
  debug          = "${var.debug}"
  namespace      = "${kubernetes_namespace.hub.metadata.0.name}"
  admin_password = "${var.firefly_admin_password}"
  max_jvm_size   = "${var.firefly_max_jvm_size}"
  mem_limit      = "${var.firefly_container_mem_limit}"
  cpu_limit      = "${var.firefly_container_cpu_limit}"
  uid            = "${var.firefly_container_uid}"
  nfs_server_ip  = "${module.fileserver.ip}"
  hostname       = "${var.hostname}"
  firefly_route  = "${var.firefly_route}"
}

module "jupyterhub" {
  source                         = "./modules/jupyterhub"
  debug                          = "${var.debug}"
  hostname                       = "${var.hostname}"
  namespace                      = "${kubernetes_namespace.hub.metadata.0.name}"
  lab_selector_title             = "${var.lab_selector_title}"
  oauth_provider                 = "${var.oauth_provider}"
  allow_dask_spawn               = "${var.allow_dask_containers ? "TRUE" : ""}"
  restrict_lab_nodes             = "${var.restrict_lab_nodes ? "TRUE" : "" }"
  restrict_dask_nodes            = "${var.restrict_dask_nodes ? "TRUE" : "" }"
  repo_host                      = "${local.lab_repo_host}"
  repo_owner                     = "${local.lab_repo_owner}"
  repo_name                      = "${local.lab_repo_name}"
  lab_image                      = "${var.lab_image}"
  lab_idle_timeout               = "${var.lab_idle_timeout}"
  tiny_max_cpu                   = "${var.tiny_max_cpu}"
  mb_per_cpu                     = "${var.mb_per_cpu}"
  lab_size_range                 = "${var.lab_size_range}"
  size_index                     = "${var.size_index}"
  lab_nodejs_max_mem             = "${var.lab_nodejs_max_mem}"
  hub_route                      = "${var.hub_route}"
  firefly_route                  = "${var.firefly_route}"
  auto_repo_urls                 = "${join(",",var.auto_repo_urls)}"
  github_allowed_organizations   = "${local.github_allowed_organizations}"
  github_forbidden_organizations = "${local.github_forbidden_organizations}"
  cilogon_allowed_groups         = "${local.cilogon_allowed_groups}"
  cilogon_forbidden_groups       = "${local.cilogon_forbidden_groups}"
  oauth_client_id                = "${var.oauth_client_id}"
  oauth_secret                   = "${var.oauth_secret}"
  session_db_url                 = "${var.session_db_url}"
  cluster_admin                  = "${local.cluster_admin}"
  external_firefly_url           = "${var.external_firefly_url}"
}

module "proxy" {
  source    = "./modules/proxy"
  hostname  = "${var.hostname}"
  namespace = "${kubernetes_namespace.hub.metadata.0.name}"
  hub_route = "${var.hub_route}"
}

module "nginx_ingress" {
  source        = "./modules/nginx_ingress"
  cluster_admin = "${local.cluster_admin}"
}
