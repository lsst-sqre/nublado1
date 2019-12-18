resource "kubernetes_role_binding" "prepuller" {
  metadata {
    name      = "prepuller"
    namespace = "${var.prepuller_namespace}"
  }

  subject {
    kind      = "ServiceAccount"
    name      = "prepuller"
    namespace = "${var.prepuller_namespace}"
  }

  role_ref {
    kind      = "Role"
    name      = "prepuller"
    api_group = "rbac.authorization.k8s.io"
  }
}
