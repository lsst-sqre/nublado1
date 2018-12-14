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

resource "kubernetes_namespace" "hub_namespace" {
  name = "${local.kubernetes_cluster_namespace}"
}
