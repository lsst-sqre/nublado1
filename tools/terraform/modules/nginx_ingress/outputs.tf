output "ip" {
  value = "${kubernetes_service.ingress_nginx.load_balancer_ingress.0.ip}"
}
