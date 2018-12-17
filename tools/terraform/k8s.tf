# Get current service account, which should be able to talk to the project
#  we specified

data "google_client_config" "current" {}

# Provider

provider "kubernetes" {
  load_config_file       = false
  host = "${google_container_cluster.cluster.endpoint}"
  cluster_ca_certificate = "${base64decode(google_container_cluster.cluster.master_auth.0.cluster_ca_certificate)}"
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
}
