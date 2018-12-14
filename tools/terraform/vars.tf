/* Start with variables for external access: 
    * hostname
    * TLS parameters
    * Application routes
*/

variable "hostname" {
  description = "Fully-qualified, externally-accessible (needed for OAUth callback), hostname of Jupyter endpoint"
}

variable "tls_dir" {
  description = "Local directory holding cert.pem, key.pem, chain.pem, and optionally dhparam.pem"
}

# How do I default these to be the filename appended to tls_dir if tls_dir is
#  set?

variable "tls_cert" {
  description = "Local path to TLS certificate cert.pem"
}

variable "tls_key" {
  description = "Local path to secret key key.pem"
}

variable "tls_root_chain" {
  description = "Local path to root certificate chain chain.pem"
}

variable "tls_dhparam" {
  description = "Local path to Diffie-Hellman parameter file dhparam.pem.  If not set it will be generated on the fly, which can be very slow."
}

variable "dhparam_bits" {
  description = "Size of DH parameters; only used if dhparam.pem is generated."
  dparam_bits = 2048
}

variable "hub_route" {
  description = "Route to JupyterHub.  If it is '/', the landing page will not be installed; otherwise it will"
  default = "/nb/"
}

variable "firefly_route" {
  description = "Route to firefly.  If it is the empty string, firefly will not be installed"
  default = "/firefly/"
}

variable "oauth_provider" {
  description = "One of 'github' or 'cilogon'"
  default = "github"
}

/* Kubernetes parameters (derived from hostname) */

variable "kubernetes_cluster_name" {
  description = "Name of kubernetes cluster."
  default = "FIXME: should be hostname with dots transformed to dashes"
}

variable "kubernetes_cluster_namespace" {
  description = "Namespace for JupyterHub and infrastructure components"
  default = "FIXME: should be first component of hostname"
}

/* GKE parameters */

variable "gke_project" {
  description ="GKE project to install under"
  default = "FIXME: user default from environment."
}

variable "gke_zone" {
  description = "GCE zone of kubernetes nodes"
  default = "us-central1-a"
}

variable "gke_node_count" {
  description = "Number of kubernetes nodes in node pool"
  default = 3
}

variable "gke_machine_type" {
  description = "GCE Machine type for kubernetes nodes"
  default = "n1-standard-4"
}

variable "gke_default_local_volume_size_gigabytes" {
  description = "Node local volume size (mostly for image cache)"
  default = 200
}

/* Fileserver parameters */

# If set, external fileserver is used

variable "external_fileserver_ip" {
  description = "IP of NFS server; must be accessible from Hub, Firefly, and JupyterLab"
}

variable "volume_size_gigabytes" {
  description = "Size of fileserver exported volume in gigabytes.  Note that GKE caps the volume size at 500 unless you ask for the limits to be raised"
  default = 20
}

/* OAuth parameters */

variable "oauth_client_id" {
  description = "Client ID to use for OAuth authentication"
}

variable "oauth_secret" {
  description = "OAuth secret for authentication"
}

variable "allowed_groups" {
  description = "List of groups allowed to use Jupyter"
}

# We have both of these in preparation for chained authentication flows.

variable "github_allowed_organizations" {
  description = "GitHub organizations allowed to log in"
  default = "FIXME: allowed_groups if oauth_type is 'github'"
}

variable "cilogon_allowed_groups" {
  description = "CILogon groups allowed to log in"
  default = "FIXME: allowed_groups if oauth_type is 'cilogon'"
}

variable "forbidden_groups" {
  description = "List of groups forbidden from using Jupyter"
}

variable "github_forbidden_organizations" {
  description = "List of GitHub organizations forbidden from using Jupyter"
}

variable "cilogon_forbidden_groups" {
  description = "List of CILogon groups forbidden from using Jupyter"
}

/* Session Database params */

variable "session_db_url" {
  description = "session storage location; any SQLAlchemy URL will work"
  default = "sqlite:////home/jupyter/jupyterhub.sqlite"
}
