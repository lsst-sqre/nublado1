resource "kubernetes_role_binding" "prepuller" {
  metadata {
    name = "prepuller"
    namespace = "${var.prepuller_namespace}"
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

  depends_on = [ "kubernetes_service_account.prepuller",
    "kubernetes_role.prepuller" ]
}
