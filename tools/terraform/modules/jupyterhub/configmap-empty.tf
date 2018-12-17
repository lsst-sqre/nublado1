resource "kubernetes_config_map" "jupyterhub" {
  metadata {
    name = "jupyterhub"
  }

  data {
  }
}
