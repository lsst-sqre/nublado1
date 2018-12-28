resource "kubernetes_service" "landing_page" {
  metadata {
    name      = "landing-page"
    namespace = "${var.namespace}"
  }

  spec {
    type = "NodePort"

    port {
      name        = "http"
      port        = 8080
      target_port = 8080
    }

    selector {
      name = "landing-page"
    }
  }
}
