variable "quantity" {
  description = "Module-wide substitute for 'count'"
}

variable "debug" {
  description = "enable debug logging"
}

variable "namespace" {
  description = "k8s namespace in which to run Firefly"
}

variable "admin_password" {
  description = "Firefly administrative password"
}

variable "max_jvm_size" {
  description = "Maximum JVM size for Firefly"
}

variable "mem_limit" {
  description = "Maximum container size for Firefly"
}

variable "cpu_limit" {
  description = "Maximum number of CPU cores for Firefly container"
}

variable "uid" {
  description = "UID under which to run Firefly"
}
