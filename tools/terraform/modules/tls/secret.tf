resource "kubernetes_secret" "tls" {
  metadata {
    name = "tls"
  }
  data {
    "tls.crt" = "${file("${var.tls_cert}")}"
    "tls.key" = "${file("${var.tls_key}")}"
    "root_chain.pem" = "${file("${var.tls_root_chain}")}"
    "dhparam.pem" = "${file("${var.tls_dhparam}")}"
  }
}
