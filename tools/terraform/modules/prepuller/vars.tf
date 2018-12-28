locals {
  _ten_min               = "${timeadd(timestamp(),"10m")}"
  _prepuller_minute_list = ["${split(":",local._ten_min)}"]
  prepuller_minute       = "${local._prepuller_minute_list[1]}"
}

variable "debug" {}

variable "image_list" {}

variable "owner" {}

variable "no_scan" {}

variable "repo" {}

variable "image_name" {}

variable "dailies" {}

variable "weeklies" {}

variable "releases" {}

variable "insecure" {}

variable "port" {}

variable "sort_field" {}

variable "command" {}

variable "prepuller_namespace" {}
