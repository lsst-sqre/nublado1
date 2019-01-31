variable "namespace" {
  description = "k8s namespace in which to run CHP"
}

variable "hub_route" {
  description = "HTTP path route to Hub"
}

variable "hostname" {
  description = "FQDN of Jupyter"
}
