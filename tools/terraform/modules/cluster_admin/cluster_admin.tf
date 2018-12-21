resource "kubernetes_cluster_role_binding" "cluster_admin_binding" {
  metadata {
    name = "cluster-admin-binding"
  }
  role_ref {
    api_group = "rbac.authorization.k8s.io"
    kind = "ClusterRole"
    name = "cluster-admin"
  }
  subject {
    kind = "User"
    name = "${var.gcloud_account}"
    api_group = "rbac.authorization.k8s.io"
  }
}
