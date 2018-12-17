resource "kubernetes_cluster_role_binding" "jupyterhub" {
  metadata {
    name = "jupyterhub"
  }
  subject {
    kind = "ClusterRole"
    name = "jupyterhub"
    namespace = "${var.namespace}"
  }
  role_ref {
    api_group = "rbac.authorization.k8s.io"
    name = "jupyterhub"
    kind = "ClusterRole"
  }
}
