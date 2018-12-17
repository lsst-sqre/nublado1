resource "kubernetes_namespace" "hub_namespace" {
  metadata {
    name = "${var.namespace}"
  }
}
