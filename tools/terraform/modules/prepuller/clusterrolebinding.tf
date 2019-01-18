resource "kubernetes_cluster_role_binding" "prepuller" {
  metadata {
    name = "prepuller"
  }

  subject {
    kind      = "ServiceAccount"
    name      = "prepuller"
    namespace = "${var.prepuller_namespace}"
  }

  role_ref {
    api_group = ""
    name      = "prepuller"
    kind      = "ClusterRole"
  }

  depends_on = [ "kubernetes_cluster_role.prepuller",
    "kubernetes_service_account.prepuller" ]
}
