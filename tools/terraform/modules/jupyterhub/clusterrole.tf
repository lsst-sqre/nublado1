resource "kubernetes_cluster_role" "jupyterhub" {
  metadata {
    name = "jupyterhub"
  }

  rule = {
    api_groups = [""]
    resources  = ["pods", "events", "namespaces", "serviceaccounts", "persistentvolumeclaims", "persistentvolumes", "resourcequotas"]
    verbs      = ["get", "list", "create", "watch", "delete"]
  }

  rule = {
    api_groups = ["rbac.authorization.k8s.io"]
    resources  = ["roles", "rolebindings"]
    verbs      = ["get", "list", "create", "delete"]
  }
}
