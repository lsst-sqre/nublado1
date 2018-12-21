resource "kubernetes_service" "ingress_nginx" {
  metadata {
    name      = "ingress-nginx"
    namespace = "ingress-nginx"

    labels {
      "app.kubernetes.io/name"    = "ingress-nginx"
      "app.kubernetes.io/part-of" = "ingress-nginx"
    }
  }

  spec {
    external_traffic_policy = "Local"
    type                    = "LoadBalancer"

    selector {
      "app.kubernetes.io/name"    = "ingress-nginx"
      "app.kubernetes.io/part-of" = "ingress-nginx"
    }

    port {
      name        = "http"
      port        = 80
      target_port = 80
    }

    port {
      name        = "https"
      port        = 443
      target_port = 443
    }
  }

  depends_on = ["kubernetes_namespace.ingress_nginx"]
}
