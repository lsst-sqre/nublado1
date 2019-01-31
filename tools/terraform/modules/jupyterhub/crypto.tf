resource "random_id" "crypto_key" {
  keepers = {
    hostname = "${var.hostname}"
  }

  byte_length = 32
}

resource "random_id" "configproxy_auth_token" {
  keepers = {
    hostname = "${var.hostname}"
  }

  byte_length = 32
}
