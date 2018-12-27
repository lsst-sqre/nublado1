module "route53" {
  source      = "./modules/route53"
  aws_zone_id = "${var.aws_zone_id}"
  hostname    = "${var.hostname}"
  ip          = "${local.endpoint_ip}"
}
