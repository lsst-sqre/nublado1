resource "kubernetes_deployment" "landing_page" {
  metadata {
    name      = "landing-page"
    namespace = "${var.namespace}"
  }

  spec {
    selector {
      name = "landing-page"
    }

    template {
      metadata {
        name = "landing-page"

        labels {
          name = "landing-page"
        }
      }

      spec {
        container {
          name              = "landing-page"
          image_pull_policy = "Always"
          image             = "lsstsqre/tiny-static-server"

          volume_mount = [
            {
              "name"       = "landing-page-www"
              "mount_path" = "/www"
            },
          ]

          port {
            container_port = 8080
            name           = "http"
          }

          env = [
            {
              name  = "HTTP_PORT"
              value = 8080
            },
            {
              name  = "HTTP_CONTENT_DIR"
              value = "www"
            },
          ]
        }

        volume {
          name = "landing-page-www"

          config_map {
            name         = "landing-page-www"
            default_mode = 0644
          }
        }
      }
    }
  }
}
