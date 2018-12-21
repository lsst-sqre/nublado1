resource "kubernetes_service" "firefly" {
  metadata = {
    name = "firefly"

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
