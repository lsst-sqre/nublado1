resource "kubernetes_ingress" "firefly" {
  metadata {
    name      = "firefly"
    namespace = "${var.namespace}"

    annotations {
      "kubernetes.io/ingress.class"                       = "nginx"
      "nginx.ingress.kubernetes.io/affinity"              = "cookie"
      "nginx.ingress.kubernetes.io/proxy-body-size"       = "0m"
      "nginx.ingress.kubernetes.io/ssl-redirect"          = "true"
      "nginx.ingress.kubernetes.io/rewrite-target"        = "${var.firefly_route}"
      "nginx.ingress.kubernetes.io/configuration-snippet" = "proxy_set_header X-Forwarded-Proto https;\nproxy_set_header X-Forwarded-Port 443;\nproxy_set_header X-Forwarded-Path ${var.firefly_route};"
    }
  }

  spec {
    tls {
      hosts       = ["${var.hostname}"]
      secret_name = "tls"
    }

    rule {
      host = "${var.hostname}"

      http {
        path {
          path_regex = "${var.firefly_route}"

          backend {
            service_name = "firefly"
            service_port = "8080"
          }
        }
      }
    }
  }
}
