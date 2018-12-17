resource "kubernetes_persistent_volume_claim" "jupyterhub-home" {
  metadata {
    name = "jupyterhub-home"
    namespace = "${var.namespace}"
    labels {
      name = "jupyterhub-home"
    }
  }
  spec {
    access_modes = [ "ReadWriteOnce" ]
    resources {
      requests {
        storage = "1Gi"
      }
    }
  }
}
