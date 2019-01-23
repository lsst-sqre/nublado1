resource "kubernetes_service_account" "prepuller" {
  metadata {
    name      = "prepuller"
    namespace = "${var.prepuller_namespace}"
  }
}
