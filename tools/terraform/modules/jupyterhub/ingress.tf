resource "kubernetes_ingress" "jupyterhub" {
  metadata {
    name = "jld-hub"

    annotations {
      "kubernetes.io/ingress.class"                       = "nginx"
      "nginx.ingress.kubernetes.io/affinity"              = "cookie"
      "nginx.ingress.kubernetes.io/proxy-body-size"       = "0m"
      "nginx.ingress.kubernetes.io/ssl-redirect"          = "true"
      "nginx.ingress.kubernetes.io/rewrite-target"        = "${var.hub_route}"
      "nginx.ingress.kubernetes.io/configuration-snippet" = "proxy_set_header X-Forwarded-Proto https;\nproxy_set_header X-Forwarded-Port 443;\nproxy_set_header X-Forwarded-Path ${var.hub_route};"
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
          path_regex = "${var.hub_route}"

          backend {
            service_name = "jld-hub"
            service_port = "8000"
          }
        }
      }
    }
  }
}
