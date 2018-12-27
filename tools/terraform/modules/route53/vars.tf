variable "hostname" {
  description = "FQDN of Jupyter endpoint for A record"
}

variable "ip" {
  description = "IP address of A record"
}

variable "aws_zone_id" {
  description = "Zone ID for Route 53 zone"
}
