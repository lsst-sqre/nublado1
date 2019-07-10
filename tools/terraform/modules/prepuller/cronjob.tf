resource "kubernetes_cron_job" "prepuller" {
  metadata {
    name      = "prepuller"
    namespace = "${var.prepuller_namespace}"
  }

  spec {
    schedule = "${local.prepuller_minute} * * * *"

    job_template {
      spec {
        template {
          spec {
            restart_policy       = "Never"
            service_account_name = "prepuller"

            container {
              name              = "prepuller"
              image_pull_policy = "Always"
              image             = "lsstsqre/prepuller"

              env = [
                {
                  name  = "DEBUG"
                  value = "${var.debug}"
                },
                {
                  name  = "PREPULLER_IMAGE_LIST"
                  value = "${var.image_list}"
                },
                {
                  name  = "PREPULLER_NO_SCAN"
                  value = "${var.no_scan}"
                },
                {
                  name  = "PREPULLER_REPO"
                  value = "${var.repo}"
                },
                {
                  name  = "PREPULLER_OWNER"
                  value = "${var.owner}"
                },
                {
                  name  = "PREPULLER_IMAGE_NAME"
                  value = "${var.image_name}"
                },
		{
                  name  = "PREPULLER_EXPERIMENTALS"
                  value = "${var.experimentals}"
                },
                {
                  name  = "PREPULLER_DAILIES"
                  value = "${var.dailies}"
                },
                {
                  name  = "PREPULLER_WEEKLIES"
                  value = "${var.weeklies}"
                },
                {
                  name  = "PREPULLER_DAILIES"
                  value = "${var.releases}"
                },
                {
                  name  = "PREPULLER_INSECURE"
                  value = "${var.insecure}"
                },
                {
                  name  = "PREPULLER_PORT"
                  value = "${var.port}"
                },
                {
                  name  = "PREPULLER_SORT_FIELD"
                  value = "${var.sort_field}"
                },
                {
                  name  = "PREPULLER_COMMAND"
                  value = "${var.command}"
                },
                {
                  name  = "PREPULLER_NAMESPACE"
                  value = "${var.prepuller_namespace}"
                },
              ]
            }
          }
        }
      }
    }
  }
}
