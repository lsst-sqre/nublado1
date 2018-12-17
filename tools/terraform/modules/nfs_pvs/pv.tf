resource "kubernetes_persistent_volume" "home" {
  metadata {
    name = "home-${var.namespace}"
    annotations = {
    }
  }
  spec {
    capacity {
      storage = "${var.capacity}Gi"
    }
    access_modes = [ "ReadWriteMany" ]
    persistent_volume_source = {
      nfs = {
        server = "${var.server_ip}"
        path = "/exports/home"
      }
    }
    storage_class_name = "fast"
    persistent_volume_reclaim_policy = "retain"
  }
}

resource "kubernetes_persistent_volume" "project" {
  metadata {
    name = "project-${var.namespace}"
    annotations = {
    }
  }
  spec {
    capacity {
      storage = "${var.capacity}Gi"
    }
    access_modes = [ "ReadWriteMany" ]
    persistent_volume_source = {
      nfs = {
        server = "${var.server_ip}"
        path = "/exports/project"
      }
    }
    storage_class_name = "fast"
    persistent_volume_reclaim_policy = "retain"
  }
}

resource "kubernetes_persistent_volume" "scratch" {
  metadata {
    name = "scratch-${var.namespace}"
    annotations = {
    }
  }
  spec {
    capacity {
      storage = "${var.capacity}Gi"
    }
    access_modes = [ "ReadWriteMany" ]
    persistent_volume_source = {
      nfs = {
        server = "${var.server_ip}"
        path = "/exports/scratch"
      }
    }
    storage_class_name = "fast"
    persistent_volume_reclaim_policy = "retain"
  }
}

resource "kubernetes_persistent_volume" "datasets" {
  metadata {
    name = "datasets-${var.namespace}"
    annotations = {
    }
  }
  spec {
    capacity {
      storage = "${var.capacity}Gi"
    }
    access_modes = [ "ReadOnlyMany" ]
    persistent_volume_source = {
      nfs = {
        server = "${var.server_ip}"
        path = "/exports/datasets"
      }
    }
    storage_class_name = "fast"
    persistent_volume_reclaim_policy = "retain"
  }
}
