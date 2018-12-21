# The Google provider itself

provider "google" {
  zone    = "${local.gke_zone}"
  project = "${var.gke_project}"
}

# Create cluster

resource "google_container_cluster" "jupyter" {
  name               = "${local.kubernetes_cluster_name}"
  initial_node_count = "${var.gke_node_count}"

  addons_config {
    horizontal_pod_autoscaling {
      disabled = true
    }

    kubernetes_dashboard {
      disabled = true
    }
  }

  node_config {
    disk_size_gb = "${var.gke_default_local_volume_size_gigabytes}"
    disk_type    = "pd-ssd"
    machine_type = "${var.gke_machine_type}"
  }
}
