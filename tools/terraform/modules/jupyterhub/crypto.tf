resource "random_id" "crypto_key" {
  keepers = {
    hostname = "${var.hostname}"
  }

  byte_length = 32
}
