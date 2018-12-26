resource "kubernetes_service" "firefly" {
  metadata = {
    name      = "firefly"
    namespace = "${var.namespace}"

    labels = {
      name = "firefly"
    }
  }

  spec {
    type = "NodePort"

    port {
      name        = "tomcat"
      port        = 8080
      target_port = 8080
      protocol    = "TCP"
    }

    selector {
      name = "firefly"
    }
  }
}
