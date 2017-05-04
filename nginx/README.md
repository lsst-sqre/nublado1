# k8s-jupyterlabdemo-nginx

This is a container to terminate TLS for `jupyterlabdemo.lsst.codes` at
GKE.  It is hoped that it is also a model for generic TLS termination of
Kubernetes services, or indeed for a generic nginx reverse proxy.

The goal of this particular configuration is to receive an `A+`
certification from SSL Labs.  In this particular instance:
[SSL Labs](https://www.ssllabs.com/ssltest/analyze.html?d=jupyterlabdemo.lsst.codes
"SSL Labs certification")

## Usage

There are two types of configuration used in the container: Kubernetes
secrets, and the nginx configuration itself.  Some of the nginx
configuration is created at runtime by substitution from the
environment.

### Secrets

First you will need to populate secrets.
`kubernetes/k8s-api-nginx-secrets.template.yaml` contains the hostname,
and `kubernetes/ssl-proxy-secrets.template.yaml` contains the host
certificate, host key, DH parameters, and certificate chain for OCSP
stapling.

This organization is a holdover from using GKE Ingress resources; there
is no functional reason they couldn't be combined into a single secret
set.

In each case, copy the template file to a scratch file, replace the
field contents with the base64 encodings of the various
certificates/keys/chains, and `kubectl create -f` that file.

#### Creating containers

After that, all you need to do is `kubectl create -f
kubernetes/k8s-jupyterlabdemo-nginx-deployment.yml` and `kubectl create
-f k8s-jupyterlabdemo-nginx-service.yml` within the same cluster as the
microservices you're creating.

### Configuration of nginx

The `nginx.conf` file contains both TLS settings and proxy mappings.

#### TLS Settings

SSL settings are largely taken from [Strong SSL Security on
nginx](https://raymii.org/s/tutorials/Strong_SSL_Security_On_nginx.html
"Strong SSL Security on nginx").

#### Proxy Mappings

The mappings rely on the fact that within a single cluster, the hosts
and ports of the backend microservices will be exposed in the
environment.  `entrypoint.sh` performs template substitution, and needs
to be changed as new services are added.  So, of course, does
`nginx.conf`: a new location stanza will be required for each new
service.

Note that it will be necessary to restart the container if the backends
change IP address or port, since the substitution is statically
performed at proxy initialization.

There is some slightly tricky boilerplate to allow WebSocket proxying.

