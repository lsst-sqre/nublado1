resource "kubernetes_storage_class" "fast" {
  metadata {
    name = "fast"

    labels {
      name = "fast"
    }
  }

  storage_provisioner = "kubernetes.io/gce-pd"

  parameters {
    type = "pd-ssd"
  }
}
