locals {
  "config_loader" = "${path.module}/config"
  "config_path"   = "${local.config_loader}/jupyterhub_config.d"
}

data "local_file" "jupyterhub_config_py" {
  filename = "${local.config_loader}/jupyterhub_config.py"
}

data "local_file" "00-preamble_py" {
  filename = "${local.config_path}/00-preamble.py"
}

data "local_file" "10-authenticator_py" {
  filename = "${local.config_path}/10-authenticator.py"
}

data "local_file" "20-spawner_py" {
  filename = "${local.config_path}/20-spawner.py"
}

data "local_file" "30-environment_py" {
  filename = "${local.config_path}/30-environment.py"
}

resource "kubernetes_config_map" "jupyterhub_config" {
  metadata {
    name      = "jupyterhub-config"
    namespace = "${var.namespace}"
  }

  data {
    "jupyterhub_config.py" = "${data.local_file.jupyterhub_config_py.content}"
    "00-preamble.py"       = "${data.local_file.00-preamble_py.content}"
    "10-authenticator.py"  = "${data.local_file.10-authenticator_py.content}"
    "20-spawner.py"        = "${data.local_file.20-spawner_py.content}"
    "30-environment.py"    = "${data.local_file.30-environment_py.content}"
  }
}
