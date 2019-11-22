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
    api_group = "rbac.authorization.k8s.io"
    name      = "prepuller"
    kind      = "ClusterRole"
  }
}
