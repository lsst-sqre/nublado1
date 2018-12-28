resource "kubernetes_cluster_role" "prepuller" {
  metadata {
    name = "prepuller"
  }

  rule = {
    api_groups = [""]
    resources  = ["nodes"]
    verbs      = ["list"]
  }
}
