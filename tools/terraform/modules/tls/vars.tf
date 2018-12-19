variable "tls_cert" {
  description = "TLS certificate"
}

variable "tls_key" {
  description = "TLS secret key"
}

variable "tls_root_chain" {
  description = "TLS certificate chain to root CA"
}

variable "tls_dhparam" {
  description = "DH parameters"
  default = ""
}
    
