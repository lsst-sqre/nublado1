variable "volume_size" {
  description = "Volume size in GiB for persistent storage"
}

variable "namespace" {
  description = "JupyterHub namespace"
}

variable "ip" {
  description = "IP of external fileserver; empty string for 'create'"
}

locals {
  "quantity" = "${var.ip == "" ? 1 : 0}"
}
