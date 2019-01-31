resource "kubernetes_service" "proxy" {
  metadata = {
    name      = "proxy"
    namespace = "${var.namespace}"

    labels = {
      name = "proxy"
    }
  }

  spec {
    type = "NodePort"

    port {
      name        = "http"
      port        = 8000
      target_port = 8000
      protocol    = "TCP"
    }

    port {
      name        = "api"
      port        = 8001
      target_port = 8001
      protocol    = "TCP"
    }

    selector {
      name = "proxy"
    }
  }
}
