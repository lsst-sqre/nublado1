resource "kubernetes_deployment" "firefly" {
  count = "${var.quantity}"

  metadata {
    name = "firefly"

    labels {
      name = "firefly"
    }

    namespace = "${var.namespace}"
  }

  spec {
    selector {
      name = "firefly"
    }

    template {
      metadata {
        name = "firefly"

        labels {
          name = "firefly"
        }
      }

      spec {
        container {
          name              = "firefly"
          image_pull_policy = "Always"
          image             = "ipac/firefly:lsst-dev"

          security_context {
            "run_as_user" = "${var.uid}"
          }

          volume_mount = [
            {
              "name"       = "scratch"
              "mount_path" = "/scratch"
            },
          ]

          resources {
            limits {
              memory = "${var.mem_limit}"
              cpu    = "${var.cpu_limit}"
            }

            requests {
              memory = "3G"
              cpu    = "0.8"
            }
          }

          env = [
            {
              name  = "MANAGER"
              value = "FALSE"
            },
            {
              name  = "FIREFLY_OPTS"
              value = "-Dvisualize.fits.search.path=/scratch/firefly"
            },
            {
              name  = "MAX_JVM_SIZE"
              value = "${var.max_jvm_size}"
            },
            {
              name  = "DEBUG"
              value = "${var.debug ? "TRUE" : "FALSE" }"
            },
            {
              name  = "ADMIN_PASSWORD"
              value = "${var.admin_password}"
            },
          ]
        }

        volume {
          name = "scratch"

          nfs {
            path   = "/exports/scratch"
            server = "${var.nfs_server_ip}"
          }
        }
      }
    }
  }
}
