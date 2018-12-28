locals {
  #  "config_path" = "${path.module}/config"
  # we're in tools/terraform/modules/landing_page
  "config_path" = "${path.module}/../../../../landing-page/kubernetes/config"
}

data "local_file" "LSST_logo_png" {
  filename = "${local.config_path}/LSST_logo.png"
}

data "local_file" "favicon_ico" {
  filename = "${local.config_path}/favicon.ico"
}

data "local_file" "firefly_logo_png" {
  filename = "${local.config_path}/firefly_logo.png"
}

data "local_file" "gke_logo_png" {
  filename = "${local.config_path}/gke_logo.png"
}

data "local_file" "index_html" {
  filename = "${local.config_path}/index.html"
}

data "local_file" "jupyter_logo_png" {
  filename = "${local.config_path}/jupyter_logo.png"
}

data "local_file" "kubernetes_logo_png" {
  filename = "${local.config_path}/kubernetes_logo.png"
}

data "local_file" "landing-page_css" {
  filename = "${local.config_path}/landing-page.css"
}

data "local_file" "notebook_png" {
  filename = "${local.config_path}/notebook.png"
}

resource "kubernetes_config_map" "landing_page" {
  metadata {
    name      = "landing-page-www"
    namespace = "${var.namespace}"
  }

  data {
    "LSST_logo.png"       = "${data.local_file.LSST_logo_png.content}"
    "favicon.ico"         = "${data.local_file.favicon_ico.content}"
    "firefly_logo.png"    = "${data.local_file.firefly_logo_png.content}"
    "gke_logo.png"        = "${data.local_file.gke_logo_png.content}"
    "index.html"          = "${data.local_file.index_html.content}"
    "jupyter_logo.png"    = "${data.local_file.jupyter_logo_png.content}"
    "kubernetes_logo.png" = "${data.local_file.kubernetes_logo_png.content}"
    "landing-page.css"    = "${data.local_file.landing-page_css.content}"
    "notebook.png"        = "${data.local_file.notebook_png.content}"
  }
}
