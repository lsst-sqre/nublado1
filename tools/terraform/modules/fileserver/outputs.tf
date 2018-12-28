output "ip" {
  value = "${local.quantity > 0 ? join("",kubernetes_service.fileserver.*.ip) : var.ip}"
}
