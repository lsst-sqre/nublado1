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
      name     = "api"
      port     = 8081
      protocol = "TCP"
    }

    selector {
      name = "jupyterhub"
    }
  }
}
