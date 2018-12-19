provider "aws" {
  region="us-west-2"
}

resource "aws_route53_record" "jupyter" {
  zone_id = "${var.aws_zone_id}"
  name    = "${var.hostname}"
  type    = "A"
  ttl     = "60"
  records = ["${var.ip}"]
}
