resource "kubernetes_persistent_volume_claim" "storage" {
  count = "${local.quantity}"

  metadata {
    name      = "storage"
    namespace = "${var.namespace}"
  }

  spec {
    access_modes = ["ReadWriteOnce"]

    resources {
      requests {
        storage = "${var.volume_size}Gi"
      }
    }

    storage_class_name = "fast"
  }
}
