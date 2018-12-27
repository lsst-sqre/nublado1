resource "kubernetes_service" "jupyterhub" {
  metadata {
    name = "jupyterhub"

    labels {
      name = "jupyterhub"
    }

    namespace = "${var.namespace}"
  }

  spec {
    type = "NodePort"

    port {
      name     = "http"
      port     = 8000
      protocol = "TCP"
    }

    port {
      name     = "api"
      port     = 8081
      protocol = "TCP"
    }

    selector {
      name = "jupyterhub"
    }
  }
}
