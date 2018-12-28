resource "kubernetes_ingress" "landing_page" {
  metadata {
    name      = "landing-page"
    namespace = "${var.namespace}"

    annotations {
      "kubernetes.io/ingress.class"                       = "nginx"
      "nginx.ingress.kubernetes.io/affinity"              = "cookie"
      "nginx.ingress.kubernetes.io/proxy-body-size"       = "0m"
      "nginx.ingress.kubernetes.io/ssl-redirect"          = "true"
      "nginx.ingress.kubernetes.io/rewrite-target"        = "/"
      "nginx.ingress.kubernetes.io/configuration-snippet" = "proxy_set_header X-Forwarded-Proto https;\nproxy_set_header X-Forwarded-Port 443;\nproxy_set_header X-Forwarded-Path /;"
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
          path_regex = "/"

          backend {
            service_name = "landing-page"
            service_port = 8080
          }
        }
      }
    }
  }
}
