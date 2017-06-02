# jupyterlabdemo

## Running

* `docker run -it --rm -p 8000:8000 --name jupyterlabdemo
  lsstsqre/jupyterlabdemo`

* You can log in with local (PAM) authentication.

* Or, better, build a kube evironment and run filebeat, logstashrmq,
  nginx, the hub, and the fileserver, and log in with GitHub OAuth2.

### Notebook

* Choose `LSST_Stack` as your Python kernel.  Then you can `import lsst`
  and the stack and all its pre-reqs are available in the environment.
  
### Terminal

* Start by running `. /opt/lsst/software/stack/loadLSST.bash`.  Then
  `setup lsst_distrib` and then you're in a stack shell environment.

## Building

* Each component has a `Dockerfile`.  `docker build -t <container-name>
  .` in its directory will build the container.

## Kubernetes

* Each component has a `kubernetes` directory (except for JupyterLab,
  which is spawned on demand).
  
### Fileserver

* This creates an auto-provisioned PersistentVolume by creating a
  PersistentVolumeClaim for the physical storage; then it
  stacks an NFS server atop that, adds a service for the NFS server, and
  then creates a (not namespaced) PersistentVolume representing the NFS
  export.  Then there is a (namespaced) PersistentVolumeClaim for the
  NFS export that the Lab pods will use.
  
### Hub

* The Hub component has a Deployment and a Service.  It will need an
  actual URL assigned, although you won't get to that until the Nginx
  component.  On the Hub set up a GitHub application and environment
  variables as described at https://github.com/jupyterhub/oauthenticator .
  
* Additionally define the `GITHUB_ORGANIZATION_WHITELIST` environment
  variable with a comma-separated list of organizations whose members
  should be allowed to log in.
  
### Nginx

* Nginx terminates TLS and uses the Hub Service as its backend target.
  It too has a Deployment and a Service, and additionally the TLS
  secrets. 

### Logstash

* The `filebeat` daemonset logs to a local `logstash` collector which
  uses RabbitMQ to send logs to NCSA.

### JupyterLab

* JupyterLab is launched from the Hub.  Each user gets a new pod, with a
  home directory on shared storage.  GitHub is the authentication
  source: the username is the GitHub user name, the UID is the GitHub ID
  number, and the groups are created with GIDs from the GitHub
  organizations the user is a member of, and their IDs.

