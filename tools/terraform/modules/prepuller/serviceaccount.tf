resource "kubernetes_service_account" "prepuller" {
  metadata {
    name = "prepuller"
  }
}
