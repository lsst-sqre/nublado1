resource "kubernetes_deployment" "proxy" {
  metadata {
    name = "proxy"

    labels {
      name = "proxy"
    }

    namespace = "${var.namespace}"
  }

  spec {
    selector {
      name = "proxy"
    }

    template {
      metadata {
        name = "proxy"

        labels {
          name = "proxy"
        }
      }

      spec {
        container {
          name              = "proxy"
          image_pull_policy = "Always"
          image             = "jupyterhub/configurable-http-proxy"

          resources {
            requests {
              memory = "512M"
              cpu    = "200m"
            }
          }

          command = [
            "configurable-http-proxy",
            "--ip=0.0.0.0",
            "--api-ip=0.0.0.0",
            "--api-port=8001",
            "--default-target=http://$$(HUB_SERVICE_HOST):$$(HUB_SERVICE_PORT_API)",
            "--error-target=http://$$(HUB_SERVICE_HOST):$$(HUB_SERVICE_PORT_API)/hub/error",
            "--port=8000",
          ]

          env {
            name = "CONFIGPROXY_AUTH_TOKEN"

            value_from {
              secret_key_ref {
                name = "jupyterhub"
                key  = "configproxy_auth_token"
              }
            }
          }
        }
      }
    }
  }
}
