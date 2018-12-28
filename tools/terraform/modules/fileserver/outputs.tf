output "ip" {
  #  value = "${local.quantity > 0 ? join("",kubernetes_service.fileserver.*.ip) : var.ip}"
  value = "${var.ip}" # Fix once we can create internal fileserver.
}
