resource "kubernetes_config_map" "nginx_configuration" {
  metadata {
    name = "nginx-configuration"
    namespace = "ingress-nginx"
    labels {
      "app.kubernetes.io/name" = "ingress-nginx"
      "app.kubernetes.io/part-of" = "ingress-nginx"
    }
  }
}

resource "kubernetes_config_map" "tcp_services" {
  metadata {
    name = "tcp-services"
    namespace = "ingress-nginx"
    labels {
      "app.kubernetes.io/name" = "ingress-nginx"
      "app.kubernetes.io/part-of" = "ingress-nginx"
    }
  }
}

resource "kubernetes_config_map" "udp_services" {
  metadata {
    name = "tcp-services"
    namespace = "ingress-nginx"
    labels {
      "app.kubernetes.io/name" = "ingress-nginx"
      "app.kubernetes.io/part-of" = "ingress-nginx"
    }
  }
}

resource "kubernetes_service_account" "nginx_ingress" {
  metadata {
    name = "nginx-ingress-serviceaccount"
    namespace = "ingress-nginx"
    labels {
      "app.kubernetes.io/name" = "ingress-nginx"
      "app.kubernetes.io/part-of" = "ingress-nginx"
    }
  }
}

resource "kubernetes_cluster_role" "nginx_ingress" {
  metadata {
    name = "nginx-ingress-clusterrole"
    labels {
      "app.kubernetes.io/name" = "ingress-nginx"
      "app.kubernetes.io/part-of" = "ingress-nginx"
    }
  }
  rule {
    api_groups = [ "" ]
    resources = [ "configmaps", "endpoints", "nodes", "pods", "secrets" ]
    verbs = [ "list", "watch" ]
  }
  rule {
    api_groups = [ "" ]
    resources = [ "nodes" ]
    verbs = [ "get" ]
  }
  rule {
    api_groups = [ "" ]
    resources = [ "services" ]
    verbs = [ "get", "list", "watch" ]
  }
  rule {
    api_groups = [ "extensions" ]
    resources = [ "ingresses" ]
    verbs = [ "get", "list", "watch" ]
  }
  rule {
    api_groups = [ "" ]
    resources = [ "events" ]
    verbs = [ "create", "patch" ]
  }
  rule {
    api_groups = [ "extensions" ]
    resources = [ "ingresses/status" ]
    verbs = [ "update" ]
  }
}

resource "kubernetes_role" "nginx_ingress" {
  metadata {
    name = "nginx-ingress-role"
    namespace = "ingress-nginx"
    labels {
      "app.kubernetes.io/name" = "ingress-nginx"
      "app.kubernetes.io/part-of" = "ingress-nginx"
    }
  }
  rule {
    api_groups = [ "" ]
    resources = [ "configmaps", "pods", "secrets", "namespaces" ]
    verbs = [ "get" ]
  }
  rule {
    api_groups = [ "" ]
    resources = [ "configmaps" ]
    resource_names = [ "ingress-controller-leader-nginx" ]
    verbs = [ "get", "update" ]
  }
  rule {
    api_groups = [ "" ]
    resources = [ "configmaps" ]
    verbs = [ "create" ]
  }
  rule {
    api_groups = [ "" ]
    resources = [ "endpoints" ]
    verbs = [ "get" ]
  }
}

resource "kubernetes_role_binding" "nginx_ingress" {
  metadata {
    name = "nginx-ingress-role"
    namespace = "ingress-nginx"
    labels {
      "app.kubernetes.io/name" = "ingress-nginx"
      "app.kubernetes.io/part-of" = "ingress-nginx"
    }
  }
  role_ref {
    api_group = "rbac.authorization.k8s.io"
    kind = "Role"
    name = "nginx-ingress-role"
  }
  subject = {
    kind = "ServiceAccount"
    name =  "nginx-ingress-serviceaccount"
    namespace = "ingress-nginx"
  }
}

resource "kubernetes_cluster_role_binding" "nginx_ingress" {
  metadata {
    name = "nginx-ingress-role"
    labels {
      "app.kubernetes.io/name" = "ingress-nginx"
      "app.kubernetes.io/part-of" = "ingress-nginx"
    }
  }
  role_ref {
    api_group = "rbac.authorization.k8s.io"
    kind = "ClusterRole"
    name = "nginx-ingress-clusterrole"
  }
  subject {
      kind = "ServiceAccount"
      name =  "nginx-ingress-serviceaccount"
      namespace = "ingress-nginx"
  }
}

resource "kubernetes_deployment" "nginx_ingress_controller" {
  metadata {
    name = "nginx-ingress-controller"
    namespace = "ingress-nginx"
    labels {
      "app.kubernetes.io/name" = "ingress-nginx"
      "app.kubernetes.io/part-of" = "ingress-nginx"
    }
  }
  spec {
    selector {
      "app.kubernetes.io/name" = "ingress-nginx"
      "app.kubernetes.io/part-of" = "ingress-nginx"
    }
    template {
      metadata {
        labels {
          "app.kubernetes.io/name" = "ingress-nginx"
          "app.kubernetes.io/part-of" = "ingress-nginx"
        }
        annotations {
          "prometheus.io/port" = "10254"
          "prometheus.io/scrape" = "true"
        }
      }
      spec {
	service_account_name = "nginx-ingress-serviceaccount"
	container {
	  name = "nginx-ingress-controller"
	  image = "quay.io/kubernetes-ingress-controller/nginx-ingress-controller:0.21.0"
	  args = [
	    "/nginx-ingress-controller",
	    "--configmap=$$(POD_NAMESPACE)/nginx-configuration",
	    "--tcp-services-configmap=$$(POD_NAMESPACE)/tcp-services",
	    "--udp-services-configmap=$$(POD_NAMESPACE)/udp-services",
	    "--publish-service=$$(POD_NAMESPACE)/ingress-nginx",
	    "--annotations-prefix=nginx.ingress.kubernetes.io"
	  ]
	  security_context {
	    capabilities {
	      drop = [ "ALL" ]
	      add = [ "NET_BIND_SERVICE" ]
	    }
	    run_as_user = 33
	  }
	  env {
	    name = "POD_NAME"
	    value_from {
	      field_ref {
		field_path = "metadata.name"
	      }
	    }
	  }
	  env {
	    name = "POD_NAMESPACE"
	    value_from {
	      field_ref {
		field_path = "metadata.namespace"
	      }
	    }
	  }
	  port {
	    name = "http"
	    container_port = 80
	  }
	  port {
	    name = "https"
	    container_port = 443
	  }
	  liveness_probe {
	    failure_threshold = 3
	    http_get {
	      path = "/healthz"
	      port = 10254
	      scheme = "HTTP"
	    }
	    initial_delay_seconds = 10
	    period_seconds = 10
	    success_threshold = 1
	    timeout_seconds = 1
	  }
	  readiness_probe {
	    failure_threshold = 3
	    http_get {
	      path = "/healthz"
	      port = 10254
	      scheme = "HTTP"
	    }
	    period_seconds = 10
	    success_threshold = 1
	    timeout_seconds = 1
	  }
	}
      }
    }
  }
}

resource "kubernetes_service" "ingress_nginx" {
  metadata {
    name = "ingress-nginx"
    namespace = "ingress-nginx"
    labels {
      "app.kubernetes.io/name" = "ingress-nginx"
      "app.kubernetes.io/part-of" = "ingress-nginx"
    }
  }
  spec {
    cluster_ip = ""
    external_traffic_policy = "Local"
    type = "LoadBalancer"
    selector {
      "app.kubernetes.io/name" = "ingress-nginx"
      "app.kubernetes.io/part-of" = "ingress-nginx"
    }
    port {
      name = "http"
      port = 80
      target_port = 80
    }
    port {
      "name" = "https"
      "port" = 443
      target_port = 443
    }
  }
}
