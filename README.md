# jupyterlabdemo

## Do Not Use This

If what you want to do is simply deploy a Jupyter setup under Kubernetes
you're much better off
using
[Zero to JupyterHub](https://zero-to-jupyterhub.readthedocs.io/en/latest/),
which is an excellent general tutorial for setting up
JupyterHub in a Kubernetes environment.

This cluster is much more specifically tailored to the needs
of [LSST](https://lsst.org).  If you want an example of how to set up
persistent storage for your users, how to ship logs to a remote ELK
stack, a worked example of how to subclass a spawner, or how to use an
image-spawner options menu, you may find it useful.

## Overview

The Jupyter Lab Demo is an environment that runs in a Kubernetes
cluster.  It provides GitHub OAuth2 authentication, authorization via
GitHub organization membership, a JupyterHub portal, and
spawned-on-demand JupyterLab containers.  It can also, optionally,
include a filebeat configuration to log to a remote ELK stack, an image
prepuller to speed startup even in an environment with heavy Lab image
churn, and an IPAC Firefly server.

## Running

* Log in with GitHub OAuth2.  You must be a member of one of the
  organizations listed in the GitHub Organization Whitelist, and your
  membership in that organization must be `public` rather than
  `private`. To do this go to the organisation `lsst or `lsst-sqre`
   find your name and there is a drop down which allows you to switch
   public/private . 

### Using the LSST Stack

#### Notebook

* Choose `LSST_Stack` as your Python kernel.  Then you can `import lsst`
  and the stack and all its pre-reqs are available in the environment.
  
#### Terminal

* Start by running `. /opt/lsst/software/stack/loadLSST.bash`.  Then
  `setup lsst_distrib` and then you're in a stack shell environment.

## Deploying a Kubernetes Cluster

### Requirements
 
* Begin by cloning this repository: `git clone
  https://github.com/lsst-sqre/jupyterlabdemo`.  You will be working
  with the kubernetes deployment files inside it, so it will probably be
  convenient to `cd` inside it.

* You need to start with a cluster to which you have administrative
  access.  This is created out-of-band at this point, using whatever
  tools your Kubernetes administrative interface gives you.  Use
  `kubectl config use-context <context-name>` to set the default
  context.

* We recommend creating a non-default namespace for the cluster and
  using that, with `kubectl create namespace <namespace>` followed by
  `kubectl config set-context $(kubectl config current-context)
  --namespace <namespace>`.  This step is optional.

* You will need to expose your Jupyter Lab instance to the public
  internet, and GitHub's egress IPs must be able to reach it.  This is
  necessary for the GitHub OAuth2 callback to work.

* You will need a public DNS record, accessible from wherever you are
  going to allow users to connect.  It must point to the IP address that
  will be the endpoint of the Jupyter Lab Demo.  This too is necessary
  for OAuth to work.  Create it with a short TTL and a bogus address (I
  recommend `127.0.0.1`); you will update the address once the exposed
  IP endpoint of the Jupyter cluster is known.

* You will additionally need SSL certificates that correspond to that
  DNS record; I have been using a wildcard record, but I am also very
  fond of letsencrypt.org.  If you go with letsencrypt.org then you will
  need to determine a way to answer the Let's Encrypt challenge, which
  is beyond the scope of this document.  GitHub will require that your
  certificate be signed by a CA it trusts, so you cannot use a
  self-signed certificate.

* You will need to create a GitHub application, either on your personal
  account or in an organization you administer.  Given that you're
  installing a cluster that uses GitHub organization membership to
  determine authentication decisions, you probably want to create the
  application within the primary organization you want to grant access
  to.  The `homepage URL` is simply the HTTPS endpoint of the DNS
  record, and the callback URL appends `/hub/oauth_callback` to that.

* The `jupyterhub/sample_configs` directory also contains a
  configuration to use `cilogon.org` with the NCSA identity provider.
  It can serve as a template for using a different identity provider.

* These instructions and templates generally assume Google Container
  Engine.  If you are using a different Kubernetes provider, you will
  need to adjust your processes to fit in some cases; for instance,
  auto-provisioning a PersistentVolume when presented with an
  unsatisfied PersistentVolumeClaim is a Google feature.

### Getting started using Google Cloud
You need to create a github application - this is under developer tools on the github settings page. Set this up with 
  * A url which is SOMENAME.com or such - you need to set a DNS entry up for this (or get Adam to do it for you) initially have it point to 127.0.0.1
  * You will need the secrets etc from this creation later .

One easy way to set this up is using Google cloud. 
* You can create/activate your cloud account at cloud.google.com.
* Install the Google Cloud API/SDK https://cloud.google.com/sdk/. Unpack this to some location you are happy for it to live in.
* Enable kube control  using: ` gcloud components install kubectl`
* You need to connect this to your Google account using : `gcloud init`
  this will also allow you to create a new project e.g. myname-jupyterdemo.
* You should enable the The Container Engine API in the Google Cloud console (search in the apis menu) as well as enabling billing for kubernetes(left menu).
* Now start a cluster 2 nodes with 2 cpus ok to start: `gcloud container clusters create wom-jupyter-cluster --num-nodes=2 --machine-type=n1-standard-2 --zone=us-central1-a
`
* Now we can deploy the components mentioned below e.g. 
** kubectl create -f fileserver/kubernetes/jld-fileserver-deployment.yml 
** kubectl create -f fileserver/kubernetes/jld-fileserver-storageclass.yml
** kubectl create -f fileserver/kubernetes/jld-fileserver-physpvc.yml
** kubectl create -f fileserver/kubernetes/jld-fileserver-service.yml
** cp fileserver/kubernetes/jld-fileserver-pv.template.yml  jld-fileserver-pv.yml  
   Edit the file replace the FIXME with a name like YOURNAME on the top of the file.
   Get the IP address of the cluster using `kubectl cluster-info` and put it in the FIXME a the end of the file.
   Then create the service with `kubectl create -f jld-fileserver-pv.yml` 
** kubectl create -f fileserver/kubernetes/jld-fileserver-pvc.yml
 
** kubectl create -f fs-keepalive/kubernetes/jld-keepalive-deployment.yml
** kubectl create -f prepuller/kubernetes/prepuller-daemonset.yml 
** kubectl create -f jupyterhub/kubernetes/jld-hub-service.yml 
** kubectl create -f jupyterhub/kubernetes/jld-hub-physpvc.yml 
** cp jupyterhub/kubernetes/jld-hub-secrets.template.yml .  
   Edit the file to fill in the missing information .. including the secret from above - note base64 encode ...  
   kubectl create -f jld-hub-secrets.template.yml 

**  Set the env variable export K8S_CONTEXT=`kubectl config current-context`
** Deploy the hub using the script in the jupyterhub directory `cd jupyterhub ; redeploy`


### Component Structure

* Each Jupyter Lab Demo component has a `kubernetes` directory (except
  for JupyterLab, which is spawned on demand).  The files in this
  directory are used to create the needed pods for the corresponding
  services.

* The next sections provide an ordered list of services to deploy in the
  cluster.

* Anywhere there is a template file (denoted with `.template.yml` as the
  end of the filename), it should have the template variables (usually
  denoted with `FIXME`) substituted with a value before use.

### Creating secrets

* In general, secrets are stored as base64-encoded strings within
  `<component>-secrets.yml` files.  The incantation to create a secret
  is `echo -n <secret> | base64 -i -`.  The `-n` is necessary to prevent
  a newline from being encoded at the end.

### Logging [optional]

* The logging components are located in the `logstashrmq` and `filebeat`
  directories within the repository.

* The logging architecture is as follows: `filebeat` runs as a daemonset
  (that is, exactly one container per node), and scrapes the docker logs
  from the host filesystem mounted into the container.  It sends those
  to a `logstash` container in the same cluster, which transmits the
  logs via RabbitMQ to a remote ELK stack.

* Start with `logstashrmq`.  Copy the `logstashrmq-secrets.template.yml`
  file, and paste the base64 encoding of your rabbitmq password in place
  of `FIXME`, then `kubectl create -f logstashrmq-secrets.yml` (assuming
  that's what you named your secrets file).  This is going to be a
  frequently-repeated pattern for updating secrets (and occasionally
  other deployment files) from templates.

* Create the service next with `kubectl create -f
  logstashrmq-service.yml`.  Kubernetes services simply provide fixed
  (within the cluster) virtual IP/port combinations that abstract away
  from the particular deployment pod, so you can replace the
  implementation without your other components having to care.
  
* Copy the `logstashrmq-deployment.template.yml` file, replace the
  `FIXME` fields with your RabbitMQ target host and Vhost (top-level
  exchange), and create the service with `kubectl -f
  logstashrmq-deployment.yml`.

* Next go to `filebeat`.  Add the base64-encodings of your three
  TLS files (the CA, the certificate, and the key) to a copy of
  `filebeat-secrets.template.yml`.  Create those secrets.  Copy the
  deployment template, replace the placeholder (`SHIPPER_NAME` is an
  arbitrary string so that you can find these logs on your collecting
  system; usually the cluster name is a good choice), and create the
  DaemonSet from your template-substituted file.
  
* At this point every container in your cluster will be logging to your
  remote ELK stack.

### Fileserver

* The fileserver is located in the `fileserver` directory.

* This creates an auto-provisioned PersistentVolume by creating a
  PersistentVolumeClaim for the physical storage; then it
  stacks an NFS server atop that, adds a service for the NFS server, and
  then creates a (not namespaced) PersistentVolume representing the NFS
  export.  Then there is a (namespaced) PersistentVolumeClaim for the
  NFS export that the Lab pods will use.
  
* There is also a keepalive pod that just writes to the exported volume
  periodically.  Without it the NFS server will time out from inactivity
  eventually.

* The `fileserver` component is by far the most complicated to set up
  correctly, although the `jupyterhub` component has more settings to
  configure.

* Currently we're using NFS.  At some point we probably want to use Ceph
  instead, or, even better, consume an externally-provided storage
  system rather than having to provision it ourselves.

#### Order of Operations

This is anything but obvious.  I have done it working from the steps at
https://github.com/kubernetes/kubernetes/tree/master/examples/volumes/nfs
with some minor modifications.

#### StorageClass

Create the StorageClass resource first, which will give you access to
SSD volumes:

`kubectl create -f jld-fileserver-storageclass.yml`

(the `pd-ssd` type parameter is what does that for you; this may be
Google Container Engine-specific)

#### Physical Storage PersistentVolumeClaim

Next, create a PersistentVolumeClaim (*not* a PersistentVolume!) for the
underlying storage:

`kubectl create -f jld-fileserver-physpvc.yml`

On Google Container Engine, this will automagically create a
PersistentVolume to back it.  I, at least, found this very surprising.

If you are not running under GKE you will probably need to create a
PersistentVolume for the PersistentVolumeClaim to bind.

#### NFS Service

Create a service to expose the NFS server (only inside the cluster)
with the following:

`kubectl create -f jld-fileserver-service.yml`

You will need the IP address of the service for a subsequent step.
`kubectl describe service jld-fileserver` and note the IP address.
Alternatively, `kubectl describe service jld-fileserver | grep ^IP: |
awk '{print $2}'` to get just the IP address.

#### NFS Server

The next step is to create an NFS Server that serves up the actual
disk.

`kubectl create -f jld-fileserver-deployment.yml`

I created my own NFS Server image, basing it on the stuff found inside
the gcr.io "volume-nfs" server.  You could probably just use Google's
image and it'd be fine.

If you are already in an environment where there is an available NFS
server, then you can omit actually providing your own NFS implementation
in this step and the next and simply point to the external NFS service.

#### NFS Persistent Volume

This one is where it all goes pear-shaped.

Here comes the first really maddening thing: PersistentVolumes are not
namespaced.

And here's the second one: the NFS server defined here has to be an IP
address, not a name.

And here's the third one: you need to specify local locking in the PV
options or else the notebook will simply get stuck in disk wait when it
runs.  This does mean that you really shouldn't run two pods as the same
user at the same time, certainly not pointing to the same notebook.

The first two things combine to make it tough to do a truly automated
deployment of a new Jupyterlab Demo instance, because you have to create
the service, then pull the IP address off it and use that in the PV
definition.

Copy the template (`jld-fileserver-pv.template.yml`) to a working file,
replace the `name` field with something making it unique (such as the
cluster-plus-namespace), and replace the `server` field with the IP
address of the NFS service.  Then just create the resource with `kubectl
create -f`.

If your Kubernetes provider also provides an NFS server, you can skip
the creation of the server and just point to the external service's IP
address here.

#### NFS Mount PersistentVolumeClaim

From here on it's smooth sailing.  Create a PersistentVolumeClaim
referring to the PersistentVolume just created:

`kubectl create -f jld-fileserver-pvc.yml`

And now there is a multiple-read-and-write NFS mount for your JupyterLab
containers to use.

### NFS Keepalive Service

* This service lives in `fs-keepalive`.

* All it does is periodically write a record to the NFS-mounted
  filesystem, which insures that it doesn't get descheduled when idle.
  
* Create it with `kubectl create -f jld-keepalive-deployment.yml`

### Firefly [optional]

* The Firefly server is a multi-user server developed by IPAC at
  Caltech.  This component, located in `firefly`, provides a multi-user
  server within the Kubernetes cluster.

* Create secrets from the template by copying
  `firefly-secrets.template.yml` to a working file, and then
  base64-encode and adding an admin password in place of `FIXME`.

* Create the service and then the deployment with `kubectl create -f`
  against the appropriate YAML files..  Firefly will automatically be
  available at `/firefly` with the included nginx configuration.

### Prepuller [optional]

* Prepuller is very much geared to the LSST Science Platform use case.
  It is only needed because our containers are on the order of 8GB each;
  thus the first user of any particular build on a given node would have
  to wait 10 to 15 minutes if we were not prepulling.  Even if you want
  an image prepuller, you will probably want to create your own version
  of `get_builds.py` that finds the containers you want to use.
  Replacing `imagepurger` would be wise as well, assuming you do not
  have near-infinite storage on each node.
    
* `prepuller` is the location of this component.

* The `prepuller-daemonset.yml` file can be used as an input to `kubectl
  create -f` without modifications, if you're using this image.

### JupyterHub

This is the most complex piece, and is the one that requires the most
customization on your part.

* This is located in `jupyterhub`.

* Start by creating the `jld-hub-service` component.

* Next, create the Persistent Volume Claim: `kubectl create -f
  jld-hub-physpvc.yml`.  The Hub needs some persistent storage so its
  knowledge of user sessions survives a container restart.

* Create a file from the secrets template.  Populate this secrets file
  with the following (base64-encoded):
  
  1. The `Client ID`, `Client Secret`, and `Callback URL` from the
     OAuth2 Application you registered with GitHub at the beginning.
  2. `github_organization_whitelist` is a comma-separated list of the
     names of the GitHub organizations whose members will be allowed to
     log in.  Currently, membership in the organization must be `public`
     rather than `private` if the whitelist is to work.
  3. `session_db_url`.  If you don't know this or are happy with the
     stock sqlite3 implementation, use the URL
     `sqlite:////home/jupyter/jupyterhub.sqlite`; any RDBMS supported by
     SQLAlchemy can be used.
  4. `jupyterhub_crypto_key`; I use `openssl rand -hex 32` to get 16
     random bytes.  I use two of these separated by a semicolon as the
     secret, and the reason for that is that I can simply implement key
     rotation by, every month or so, dropping the first key, moving the
     second key to the first position, and generating a new key for the
     second position.

  Then create the secrets from that file: `kubectl create -f <filename>`.
  
* Set up your deployment environment.

  1. Set the environment variable
    `K8S_CONTEXT` to the context in which your deployment is running
    (`kubectl config current-context` will give you that information).
	
  2. If you changed the namespace, put the current namespace in the
     environment variable `K8S_NAMESPACE`.
	 
  3. If you have a repository containing a container image with multiple
     tags you wish to present as container options, you should set
     `LAB_SELECTOR_TITLE` to the title of the spawner options form,
     `LAB_REPO_HOST` to the hostname of the Docker container repository,
     `LAB_OWNER` to the name of the repository owner, and
     `LAB_REPO_NAME` to the name of the image.  The container name will
     then be `LAB_REPO_HOST`/`LAB_OWNER`/`LAB_REPO_NAME`.  If you only
     have a single image, set `LAB_IMAGE` to that container name.  It
     will default to `lsstsqre/jld-lab:latest` (with `hub.docker.com` as
     the implied repository host).

* Edit the configuration in `jupyterhub_config/jupyterhub_config.d` if
  you want to.
  - In the default configuration, the GitHub authenticator (from
    `sample_configs`) is used.
  - The files in the configuration directory are sourced in lexical sort
    order; typically they are named with a two-digit priority as a
    prefix.  Lower numbers are loaded first.
  - The preamble and spawner are common across CILogon and GitHub, but
    the authenticator and environment differ.
  - In the GitHub authenticator, we subclass GitHubLoginHandler to
    request additional scope on the token received from GitHub.
    `public_repo` allows read and write access to the user's public
    repository.  `read:org` allows enumeration of the user's
    organizations, both public and private.  `user:email` allows
    enumeration of the user's email addresses (and identification of the
    primary email).  We use these for user provisioning in the Lab
    container.
  - In the GitHub authenticator, we subclass GitHubOAuthenticator to set
    container properties from our environment and, crucially, from
    additional properties (GitHub organization membership and email
    address) we can access from the token-with-additional-scope.
  - In the common spawner class, we subclass KubeSpawner to build a
    dynamic list of kernels (current as of user login time) and then do
    additional launch-time setup, largely around changing the pod name
    to incorporate the username.

* Deploy the file using the `redeploy` script, which will create
  the `ConfigMap` resource from the JupyterHub configuration, and then
  deploy the Hub into the specified context and namespace.
  
### Nginx

Nginx terminates TLS and uses the Hub Service (and Firefly if you
installed it) as its backend target(s).

* Create secrets from the secrets template.  The three standard TLS
  files should be the CA certificate, the key, and the server
  certificate, all base64-encoded and put into the file.  `dhparam.pem`
  can be created with `openssl dhparam -out dhparam.pem 2048`, and then
  base64-encoded and inserted into the secrets YAML file.  That command
  may take some time to run.

* Create the service: `kubectl create -f nginx-service.yml`.

* Create a deployment configuration from the template.  `HOSTNAME` must
  be set to the DNS entry you created at the beginning of the
  installation.  Create the deployment.

* Retrieve the externally-visible IP address from the service.  `kubectl
  describe service jld-nginx | grep ^LoadBalancer | awk '{print $3}'`
  will work.  You may need to wait a little while before it shows up.
  
* If you already have an ingress controller you can just use the
  `nginx-ingress.yml` ingress definition; if you do this you will need
  to modify the JupyterHub configuration (set `c.JupyterHub.base_url`).

### JupyterLab

JupyterLab is launched from the Hub.

* Each user gets a new pod, with a home directory on shared storage.

* With GitHub as the authentication source, the username is the GitHub
  user name, the UID is the GitHub ID number, and the groups are created
  with GIDs from the GitHub organizations the user is a member of, and
  their IDs.

* Git will be preconfigured with a token that allows authenticated
  HTTPS pushes, and with the user's name and primary email.
  
* The CILogon authenticator will eventually have similar features, but
  those have not yet been fully developed.


### Enable DNS

* Update the DNS record you created to point at the externally-visible
  IP address you just determined.

## Using the Service

* Using a web browser, go to the DNS name you registered.  You should be
  prompted to authenticate with GitHub, to choose an image from the menu
  (if that's how you set up your JupyterHub config), and then you should
  be redirected to your lab pod.

## Building

* Each component that is unique to the demo has a `Dockerfile`.  `./bld`
  in its directory will build the container.  Unless you're in the
  lsstsqre Docker organization, you're going to need to change the
  container name label.
  
* The `bld` script requires that the description, name, and version
  labels be on separate lines.  The poor thing's not very bright.
 
* You probably don't need to rebuild anything.  If you do, it's because
  I have not made something sufficiently configurable, so I'd appreciate
  hearing about it.
