resource "kubernetes_role_binding" "prepuller" {
  metadata {
    name = "prepuller"
  }

  subject {
    kind      = "ServiceAccount"
    name      = "prepuller"
    namespace = "${var.prepuller_namespace}"
    api_group = ""
  }

  role_ref {
    kind      = "Role"
    name      = "prepuller"
    api_group = ""
  }
}
