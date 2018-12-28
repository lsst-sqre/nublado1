resource "kubernetes_role" "prepuller" {
  metadata {
    name      = "prepuller"
    namespace = "${var.prepuller_namespace}"
  }

  rule {
    api_groups = [""]
    resources  = ["pods"]
    verbs      = ["get", "list", "create", "update", "delete"]
  }
}
