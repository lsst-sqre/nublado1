[![Build Status](https://travis-ci.org/lsst-sqre/k8s-filebeat.svg?branch=master)](https://travis-ci.org/lsst-sqre/k8s-filebeat)

# k8s-filebeat

This is a utility container to ship logs from Kubernetes into an ELK
stack.  SQuaRE currently uses it to send logs from GKE to the ELK stack
at NCSA.

## Usage

First, add the secrets you will need to connect to the Logstash
implementation at the far end.  Copy
`kubernetes/filebeat-secrets.template.yaml` to a scratch file, and
include the base64 encodings of the CA certificate and your local
TLS certificate and key, as well as the logstash host name, logstash
port, shipper name (which should identify the site, e.g. "gke"), and
debug (anything but the empty string turns on debug mode).  Then run
`kubectl create -f` on that file, and then remove the file.

Then all you need to do is to create "filebeat" as a DaemonSet: 
`kubectl create -f kubernetes/filebeat-daemonset.yaml`

## How it Works

A DaemonSet resource runs one copy of the provided container on each
node in the Kubernetes cluster.  The container mounts the Docker
container logs into its own space, and then `filebeat` watches the
container logs for changes and ships them off to Logstash.  

We have an input filter defined so we log neither internal health checks
from the `kube-system` namespace (i.e. anything that comes up as a
result of `nanny_lib.go`) nor the GKE ingress healthcheck (`GET / `).

Thus, you don't have to do anything special in your container: log to
stdout/stderr as usual, and whatever is produced by the container will
wind up at the destination logstash instance.

## Limitations

We should at least put the proper endpoint into the destination host SSL
certificate so we can turn `ssl.verification_mode` back on.  Since GKE
has no defined egress, we can't really do client certificate
verification.
