resource "kubernetes_deployment" "jupyterhub" {
  metadata {
    name = "jupyterhub"
    labels {
      name = "jupyterhub"
    }
    namespace = "${var.namespace}"
  }
  spec {
    template {
      metadata {
        name = "jupyterhub"
        labels {
          name = "jupyterhub"
        }
      }
      spec {
        service_account_name = "jupyterhub"
        container {
          name = "jupyterhub"
          image_pull_policy = "Always"
          image = "lsstsqre/jld-hub"
          resources {
            limits {
              memory = "2G"
              cpu = "2.0"
            }
            requests {
              memory = "1G"
              cpu = "0.8"
            }
          }
          port {
            container_port = 8000
            name = "jupyterhub"
          }
          env {
            name = "LOGLEVEL"
            value = "INFO"
          }
          env {
            name = "LAB_SELECTOR_TITLE"
            value = "${var.lab_selector_title}"
          }
          env {
            name = "OAUTH_PROVIDER"
            value = "${var.oauth_provider}"
          }
          env {
            name = "ALLOW_DASK_SPAWN"
            value = "${var.allow_dask_spawn}"
          }
          env {
            name = "RESTRICT_LAB_NODES"
            value = "${var.restrict_lab_nodes}"
          }
          env {
            name = "RESTRICT_DASK_NODES"
            value = "${var.restrict_dask_nodes}"
          }
          env {
            name = "LAB_REPO_HOST"
            value = "${var.repo_host}"
          }
          env {
            name = "LAB_REPO_OWNER"
            value = "${var.repo_owner}"
          }
          env {
            name = "LAB_REPO_NAME"
            value = "${var.repo_name}"
          }
          env {
            name = "LAB_IMAGE"
            value = "${var.lab_image}"
          }
          env {
            name = "LAB_IDLE_TIMEOUT"
            value = "${var.lab_idle_timeout}"
          }
          env {
            name = "TINY_CPU_MAX"
            value = "${var.tiny_max_cpu}"
          }
          env {
            name = "MB_PER_CPU"
            value = "${var.mb_per_cpu}"
          }
          env {
            name = "LAB_SIZE_RANGE"
            value = "${var.lab_size_range}"
          }
          env {
            name = "SIZE_INDEX"
            value = "${var.size_index}"
          }
          env {
            name = "LAB_NODEJS_MAX_MEM"
            value = "${var.lab_nodejs_max_mem}"
          }
          env {
            name = "JUPYTERLAB_CONFIG_DIR"
            value = "/opt/lsst/software/jupyterhub/config"
          }
          env {
            name = "HUB_ROUTE"
            value = "${var.hub_route}"
          }
          env {
            name = "FIREFLY_ROUTE"
            value = "${var.firefly_route}"
          }
          env {
            name = "AUTO_REPO_URLS"
            value = "${var.auto_repo_urls}"
          }
          env {
            name = "GITHUB_ORGANIZATION_WHITELIST"
            value = "${var.github_allowed_organizations}"
          }
          env {
            name = "CILOGON_GROUP_WHITELIST"
            value = "${var.cilogon_allowed_groups}"
          }
          env {
            name = "GITHUB_ORGANIZATION_DENYLIST"
            value = "${var.github_forbidden_organizations}"
          }
          env {
            name = "CILOGON_GROUP_DENYLIST"
            value = "${var.cilogon_forbidden_groups}"
          }
          env {
            name = "OAUTH_CLIENT_ID"
            value = "${var.oauth_client_id}"
          }
          env {
            name = "OAUTH_CLIENT_SECRET"
            value = "${var.oauth_secret}"
          }
          env {
            name = "OAUTH_CALLBACK_URL"
            value = "${local.oauth_callback_url}"
          }
          env {
            name = "SESSION_DB_URL"
            value = "${var.session_db_url}"
          }
          env {
            name = "JUPYTERHUB_CRYPT_KEY"
            value = "${local.crypto_key}"
          }
          volume_mount = [
            {
              name = "jupyterhub-home"
              mount_path = "/home/jupyter"
            },
            {
              name = "jupyterhub-config"
              mount_path = "/opt/lsst/software/jupyterhub/config"
            }
          ]
        }
        volume = [
          {
            name = "jupyterhub-home"
            persistent_volume_claim = {
              claim_name = "jupyterhub-home"
            }
          },
          {
            name = "jupyterhub-config"
            config_map_ref = "jupyterhub_config"
          }
        }
      }
    }
  }
}
