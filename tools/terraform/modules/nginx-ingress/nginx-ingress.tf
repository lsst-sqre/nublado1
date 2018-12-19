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
    apiGroups = [ "" ]
    resources = [ "configmaps", "endpoints", "nodes", "pods", "secrets" ]
    verbs = [ "list", "watch" ]
  }
  rule {
    apiGroups = [ "" ]
    resources = [ "nodes" ]
    verbs = [ "get" ]
  }
  rule {
    apiGroups = [ "" ]
    resources = [ "services" ]
    verbs = [ "get", "list", "watch" ]
  }
  rule {
    apiGroups = [ "extensions" ]
    resources = [ "ingresses" ]
    verbs = [ "get", "list", "watch" ]
  }
  rule {
    apiGroups = [ "" ]
    resources = [ "events" ]
    verbs = [ "create", "patch" ]
  }
  rule {
    apiGroups = [ "extensions" ]
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
    apiGroups = [ "" ]
    resources = [ "configmaps", "pods", "secrets", "namespaces" ]
    verbs = [ "get" ]
  }
  rule {
    apiGroups = [ "" ]
    resources = [ "configmaps" ]
    resource_names = [ "ingress-controller-leader-nginx" ]
    verbs = [ "get", "update" ]
  }
  rule {
    apiGroups = [ "" ]
    resources = [ "configmaps" ]
    verbs = [ "create" ]
  }
  rule {
    apiGroups = [ "" ]
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
  subjects = [
    {
      kind = "ServiceAccount"
      name =  "nginx-ingress-serviceaccount"
      namespace = "ingress-nginx"
    }
  ]
}

resource "kubernetes_cluster_role_binding" "nginx_ingress" {
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
    kind = "ClusterRole"
    name = "nginx-ingress-clusterrole"
  }
  subjects = [
    {
      kind = "ServiceAccount"
      name =  "nginx-ingress-serviceaccount"
      namespace = "ingress-nginx"
    }
  ]
}

resource "kubernetes_deployment" "ngix_ingress_controller" {
  metadata {
    name = "nginx-ingress-controller"
    namespace = "ingress-nginx"
    labels {
      "app.kubernetes.io/name" = "ingress-nginx"
      "app.kubernetes.io/part-of" = "ingress-nginx"
    }
    spec {
      selector {
        matchLabels {
          "app.kubernetes.io/name" = "ingress-nginx"
          "app.kubernetes.io/part-of" = "ingress-nginx"
        }
      }
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
        serviceAccountName = "nginx-ingress-serviceaccount"
        containers = [
          {
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
            securityContext {
              capabilities {
                drop = [ "ALL" ]
                add = [ "NET_BIND_SERVICE" ]
              }
            }
            runAsUser = 33
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
                  fieldPath = "metadata.namespace"
                }
              }
            }
            ports = [
              {
                name = "http"
                container_port = 80
              },
              {
                name = "https"
                container_port = 443
              }
            ]
            livenessProbe {
              failure_threshold = 3
              http_get {
                path = "/healthz"
                port = 10254
                scheme = "HTTP"
              }
              initialDelaySeconds = 10
              periodSeconds = 10
              successThreshold = 1
              timeoutSeconds = 1
            }
            readinessProbe {
              failure_threshold = 3
              http_get {
                path = "/healthz"
                port = 10254
                scheme = "HTTP"
              }
              periodSeconds = 10
              successThreshold = 1
              timeoutSeconds = 1
            }
          }
        ]
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
    externalTrafficPolicy = "Local"
    type = "LoadBalancer"
    selector {
      "app.kubernetes.io/name" = "ingress-nginx"
      "app.kubernetes.io/part-of" = "ingress-nginx"
    }
    ports = [
      {
        name = "http"
        port = "80"
        targetPort = "http"
      },
      {
        "name" = "https"
        "port" = "443"
        "targetPort" = "https"
      }
    ]
  }
}
