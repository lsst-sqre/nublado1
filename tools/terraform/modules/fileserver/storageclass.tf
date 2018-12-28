resource "kubernetes_storage_class" "fast" {
  count = "${local.quantity}"

  metadata {
    name = "fast"
  }

  storage_provisioner = "kubernetes.io/gce-pd"

  parameters {
    type = "pd-ssd"
  }
}
