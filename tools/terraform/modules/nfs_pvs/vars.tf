variable "namespace" {
  description = "k8s cluster namespace"
}

variable "capacity" {
  description = "Fileserver volume capacity in GiB"
}

variable "server_ip" {
  description = "IP address of NFS server"
}

locals {
  nfs_size = "${ ( 100 * var.capacity ) / 95 }"
}
