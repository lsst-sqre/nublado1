resource "kubernetes_secret" "jupyterhub" {
  metadata {
    name = "jupyterhub"
    namespace = "${var.namespace}"
  }

  data {
    oauth_client_id = "${var.oauth_client_id}"
    oauth_secret = "${var.oauth_secret}"
    oauth_callback_url = "${local.oauth_callback_url}"
    github_allowed_organizations   = "${var.github_allowed_organizations}"
    github_forbidden_organizations = "${var.github_forbidden_organizations}"
    cilogon_allowed_groups         = "${var.cilogon_allowed_groups}"
    cilogon_forbidden_groups       = "${var.cilogon_forbidden_groups}"
    session_db_url = "${var.session_db_url}"
    crypto_key = "${local.crypto_key}"
  }
}
