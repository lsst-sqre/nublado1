resource "kubernetes_service" "fileserver" {
  count = "${local.quantity}"

  metadata {
    name      = "fileserver"
    namespace = "${var.namespace}"
  }

  spec {
    selector {
      name = "storage"
    }

    port {
      name        = "nfs"
      port        = 2049
      target_port = 2049
    }

    port {
      name        = "mountd"
      port        = 20048
      target_port = 20048
    }

    port {
      name        = "rpcbind"
      port        = 111
      target_port = 111
    }
  }
}
