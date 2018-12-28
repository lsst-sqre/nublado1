resource "kubernetes_deployment" "fileserver" {
  count = "${local.quantity}"

  metadata {
    name = "fileserver"

    labels {
      name = "fileserver"
    }

    namespace = "${var.namespace}"
  }

  spec {
    template {
      metadata {
        name = "fileserver"
      }

      spec {
        container {
          name              = "fileserver"
          image_pull_policy = "Always"
          image             = "lsstsqre/jld-fileserver"

          volume_mount = [
            {
              "name"       = "exports"
              "mount_path" = "/exports"
            },
          ]

          env = [
            {
              name  = "LOGLEVEL"
              value = "INFO"
            },
          ]

          port {
            name           = "nfs"
            container_port = 2049
          }

          port {
            name           = "mountd"
            container_port = 20048
          }

          port {
            name           = "rpcbind"
            container_port = 111
          }

          security_context {
            privileged = true
          }
        }

        volume {
          name = "storage"

          persistent_volume_claim {
            claim_name = "storage"
          }
        }
      }
    }
  }
}
