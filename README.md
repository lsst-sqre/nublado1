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
  organizations listed in the GitHub Organization Whitelist, and either
  your membership in that organization must be `public` rather than
  `private`, or `read:org` must be among the scopes granted by the
  OAuth token.

### Using the LSST Stack

#### Notebook

* Choose `LSST_Stack` as your Python kernel.  Then you can `import lsst`
  and the stack and all its pre-reqs are available in the environment.
  
#### Terminal

* Start by running `. /opt/lsst/software/stack/loadLSST.bash`.  Then
  `setup lsst_distrib` and then you're in a stack shell environment.

## Deploying a Jupyterlab Demo Kubernetes Cluster

### Quick Start: Automated Tool

See [Deployment Tool README](tools/deployment/README.md) for the
easier way to deploy.  The remainder of these instructions cover a
manual deployment.

### Requirements
 
* Begin by cloning this repository: `git clone
  https://github.com/lsst-sqre/jupyterlabdemo`.  You will be working
  with the kubernetes deployment files inside it, so it will probably be
  convenient to `cd` inside it.

* You will need `kubectl` installed in order to run the Kubernetes
  commands throughout these instructions.

* You need to start with a cluster to which you have administrative
  access.  This is created out-of-band at this point, using whatever
  tools your Kubernetes administrative interface gives you.  Use
  `kubectl config use-context <context-name>` to set the default
  context.

* We recommend creating a non-default namespace for the cluster and
  using that, with `kubectl create namespace <namespace>` followed by
  `kubectl config set-context $(kubectl config current-context)
  --namespace <namespace>`.  This step is optional.

* Since you will be creating new `Role` resources, you will need to
  grant a role binding that will allow the user you are installing as
  the power to create Roles, ClusterRoles, RoleBindings, and
  ClusterRoleBindings.  Just issue the command `kubectl create
  clusterrolebinding admin-binding --clusterrole=cluster-admin
  --user=$(gcloud config get-value account)` and that will do the trick.

* You will need to expose your Jupyter Lab instance to the public
  internet, and GitHub's egress IPs must be able to reach it.  This is
  necessary for the GitHub OAuth2 callback (or indeed any OAuth
  callback) to work.

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
  account or in an organization you administer.  If you use the setup
  given here, then you're installing a cluster that uses GitHub
  organization membership to determine authentication decisions, and
  therefore you probably want to create the application within the
  primary organization you want to grant access to.  The `homepage URL`
  is simply the HTTPS endpoint of the DNS record, and the callback URL
  appends `/hub/oauth_callback` to that.

* The `jupyterhub/sample_configs` directory also contains a
  configuration to use `cilogon.org` with the NCSA identity provider.
  If you want to use that as-is you can link the configuration directory
  to it rather than to the GitHub sample config.  It can serve as a
  model for using a different identity provider.

* These instructions and templates generally assume Google Container
  Engine.  If you are using a different Kubernetes provider, you will
  need to adjust your processes to fit in some cases; for instance,
  auto-provisioning a PersistentVolume when presented with an
  unsatisfied PersistentVolumeClaim is a Google feature.

### Component Structure

* Each Jupyter Lab Demo component has a `kubernetes` directory (except
  for JupyterLab, which is spawned on demand).  The files in this
  directory are used to create the needed pods for the corresponding
  services.

* The next sections provide an ordered list of services to deploy in the
  cluster.

* Anywhere there is a template file (denoted with `.template.yml` as the
  end of the filename), it should have the template variables (denoted
  with double curly brackets, e.g. `{{HOSTNAME}}`) substituted with a
  value before use.

### Creating secrets

* In general, secrets are stored as base64-encoded strings within
  `<component>-secrets.yml` files.  The incantation to create a secret
  is `echo -n <secret> | base64 -i -`.  The `-n` is necessary to prevent
  a newline from being encoded at the end.

* For secrets created from files (e.g. TLS certificates), the
  incantation is `base64 <secret_filename> | tr -d '\n'` to emit the
  base64 representation of the file as a single string without
  linebreaks.

### Logging [optional]

* The logging components are located in the `logstashrmq` and `filebeat`
  directories within the repository.

* The logging architecture is as follows: `filebeat` runs as a daemonset
  (that is, exactly one container per node), and scrapes the docker logs
  from the host filesystem mounted into the container.  It sends those
  to a `logstash` container in the same cluster, which transmits the
  logs via RabbitMQ to a remote ELK stack.

* Start with `logstashrmq`.  Copy the `logstashrmq-secrets.template.yml`
  file, and paste the base64 encoding of your rabbitmq password into
  the appropriate field (in place of `{{RABBITMQ_PAN_PASSWORD}}`, then
  `kubectl create -f logstashrmq-secrets.yml` (assuming that's what you
  named your secrets file).  This is going to be a frequently-repeated
  pattern for updating secrets (and occasionally other deployment files)
  from templates.

* Create the service next with `kubectl create -f
  logstashrmq-service.yml`.  Kubernetes services simply provide fixed
  (within the cluster) virtual IP/port combinations that abstract away
  from the particular deployment pod, so you can replace the
  implementation without your other components having to care.
  
* Copy the `logstashrmq-deployment.template.yml` file, replace the
  template fields with your RabbitMQ target host and Vhost (top-level
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
Google Kubernetes Engine-specific)

#### NFS Service

Create a service to expose the NFS server (only inside the cluster)
with the following:

`kubectl create -f jld-fileserver-service.yml`

You will need the IP address of the service for a subsequent step.
`kubectl describe service jld-fileserver` and note the IP address.
Alternatively, `kubectl describe service jld-fileserver | grep ^IP: |
awk '{print $2}'` to get just the IP address.

##### Physical Storage PersistentVolumeClaim

Next, create a PersistentVolumeClaim (*not* a PersistentVolume!) for the
underlying storage.  Copy the template file
`jld-fileserver-physpvc.template.yml` to a working file.  Substitute the
disk size in the `storage` field (GKE has a default quota of 500GB);
the size depends on how much local storage you expect your users to
require.

`kubectl create -f jld-fileserver-home-physpvc.yml`

On Google Kubernetes Engine, this will automagically create a
PersistentVolume to back it.  I, at least, found this very surprising.

If you are not running under GKE you will need to create a
PersistentVolume for the PersistentVolumeClaim to bind.

Note that our default deployment puts all exported volumes on a single
physical volume.  You can modify the deployment to put any or all
`scratch`, `project`, `datasets`, and `software` as separate physical
volumes which you then export.  In the real LDF environment they are of
course separate volumes managed from an external file server.

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

#### Network Volumes

##### NFS Persistent Volume

This one is where it all goes pear-shaped.

Here comes the first really maddening thing: PersistentVolumes are not
namespaced.

And here's the second one: the NFS server defined here has to be an IP
address, not a name.  (This is actually a consequence of the Kubernetes
internal DNS being namespaced and PersistentVolumes not being
namespaced, but it's not obvious.)

And here's the third one: you need to specify local locking in the PV
options or else the notebook will simply get stuck in disk wait when it
runs.  This does mean that you really shouldn't run two pods as the same
user at the same time, certainly not with the same notebook open.

The first two things combine to make it tough to do a truly automated
deployment of a new Jupyterlab Demo instance, because you have to create
the service, then pull the IP address off it and use that in the PV
definition.

Copy the template (`jld-fileserver-home-pv.template.yml`) to a working file,
replace the `name` field with something making it unique (such as the
cluster-plus-namespace), and replace the `server` field with the IP
address of the NFS service.  Replace the `storage` field with a value a
little bit smaller than the physical volume size (empirically, 95% seems
to work well).  Then just create the resource with `kubectl
create -f` against your working file.

If your Kubernetes provider also provides an NFS server, you can skip
the creation of the server and just point to the external service's IP
address here.

##### NFS Mount PersistentVolumeClaim

From here on it's smooth sailing.  Create a working file from
`jld-fileserver-home-pvc.template.yml`, substitute the `storage` field
with the value you used for the PersistentVolume immediately prior, and
then Create a PersistentVolumeClaim referring to the PersistentVolume
just created:

`kubectl create -f jld-fileserver-home-pvc.yml`

And now there is a multiple-read-and-write NFS mount for your JupyterLab
containers to use.

#### Other Volumes

As above, repeat for `scratch`, `project`, `datasets`, and `software`.
Note that `datasets` and `software` are read-only, so you will need to
install content to them from the fileserver itself (where the exported
volumes reside).

### NFS Keepalive Service

* This service lives in `fs-keepalive`.

* All it does is periodically write a record to the writeable
  NFS-mounted filesystems, which insures that the fileserver doesn't get
  descheduled when idle.
  
* Create it with `kubectl create -f jld-keepalive-deployment.yml`

### Firefly [optional]

* The Firefly server is a multi-user server developed by IPAC at
  Caltech.  This component, located in `firefly`, provides a multi-user
  server within the Kubernetes cluster.

* Create secrets from the template by copying
  `firefly-secrets.template.yml` to a working file, and then
  base64-encode and adding an admin password in place of
  `{{FIREFLY_ADMIN_PASSWORD}}`.

* Create the service and then the deployment with `kubectl create -f`
  against the appropriate YAML files.  Firefly will automatically be
  available at `/firefly` with the included nginx configuration.

### Prepuller [optional]

* Prepuller is very much geared to the LSST Science Platform use case.
  It is only needed because our containers are on the order of 8GB each;
  thus the first user of any particular build on a given node would have
  to wait 10 to 15 minutes if we were not prepulling.  We rely
  on Kubernetes to use low-water and high-water marks for managing its
  image cache; you will need to make sure that you have enough disk
  space on your nodes that your prepulled containers do not overtop the
  `image-gc-high-threshold` of `kubelet`.
    
* `prepuller` is the location of this component.


* It has several components:
  - `prepuller-serviceaccount.yml` defines a new service account:
    `kubectl create -f prepuller-serviceaccount.yml`
  - Create the `ClusterRole` and `Role`:
    `kubectl create -f prepuller-clusterrole.yml`
    `kubectl create -f prepuller-role.yml`	
  - For each of the rolebindings, copy the `template.yml` file to a
    working copy and substitute the namespace name.  Then use `kubectl
    create -f` on the resulting file.
	
* Finally, create the `CronJob` by copying the template file to a
    working file.  Substitute `{{PREPULLER_MINUTE}}` with any value
    between 0 and 59 inclusive; this is the minute of the hour at which
    the prepuller runs.  Substitute any of the additional values you
    want.  Leave the empty string `""` for any omitted value.
	- `PREPULLER_IMAGE_LIST` is a comma-separated list of images to use
      for user containers.
	- If `PREPULLER_NO_SCAN` is set to a non-empty value, the prepuller
      will not scan a Docker repository looking for the latest tags.
	- If you *are* scanning the repository, your images should have tags
      of the form `[d|w]YYYYMMDD` or `rMajMin` (e.g. `d20180219` or
      `r140`).
	- The other values can be used to change the number of
      Daily/Weekly/Release images to prepull.
	  
* After creating the working file (let's assume you called it
  `prepuller-cronjob.yml)`, run  `kubectl create -f prepuller-cronjob.yml`.

### JupyterHub

This is the most complex piece, and is the one that requires the most
customization on your part.

* This is located in `jupyterhub`.

* Start by creating the `jld-hub-service` component.

* Create a service account for `jupyterhub` so that it can manipulate
  pods using Role-Based Access Control: `kubectl create -f
  jld-hub-serviceaccount.yml`.
  
* Create a Role and a RoleBinding by copying `jld-hub-role.template.yml`
  and `jld-hub-rolebinding.template.yml` to working files, substituting
  the namespace.  Create each of those with `kubectl -f` run against the
  working file.

* Next, create the Persistent Volume Claim: `kubectl create -f
  jld-hub-physpvc.yml`.  The Hub needs some persistent storage so its
  knowledge of user sessions survives a container restart.
  
* Create a file from the secrets template.  Populate this secrets file
  with the following (base64-encoded):
  
  1. The `Client ID`, `Client Secret`, and `Callback URL` from the
     OAuth2 Application you registered with GitHub at the beginning.
  2. `github_organization_whitelist` is a comma-separated list of the
     names of the GitHub organizations whose members will be allowed to
     log in.  Either membership in the organization must be public, or
     the scopes requested for the OAuth2 token must include `read:org`
     in order for users to be able to log in based on the whitelist.
  3. `session_db_url`.  If you don't know this or are happy with the
     stock sqlite3 implementation, use the URL
     `sqlite:////home/jupyter/jupyterhub.sqlite`; any RDBMS supported by
     SQLAlchemy can be used.
  4. `jupyterhub_crypto_key`; I use `openssl rand -hex 32` to get 16
     random bytes.  I use two of these separated by a semicolon as the
     secret, and the reason for that is that I can simply implement key
     rotation by, every month or so, dropping the first key, moving the
     second key to the first position, and generating a new key for the
     second position.  The command `"r="openssl rand -hex 32"; echo
     "$(${r});$(${r})"` will generate a pair in this form for you.

  Once you have done that, create the secrets from the file: `kubectl
  create -f <filename>`.
  
* Set up your deployment environment by editing the environment
  variables in `jld-hub-deployment.yml`.

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
  - In the GitHub authenticator, we subclass GitHubOAuthenticator to set
    container properties from our environment and, crucially, from
    additional properties (GitHub organization membership and email
    address) we can access from the token-with-additional-scope.  The
    extended scope is configured at the bottom, as a configuration
    setting on our authenticator class.
  - If you're using CILogon, the setup is quite similar; scope, the
    authenticator skin, and the identity provider to use are all set as
    configurable properties of the authenticator class.
  - In the spawner class (identical between GitHub and CILogon), we
    subclass KubeSpawner to build a dynamic list of kernels (current as
    of user login time) and then do additional launch-time setup,
    largely around changing the pod name to incorporate the username.

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

* Update the DNS record with the newly-determined externally-visible
  address.  This is another piece that will be challenging to script
  because of the wide variety of APIs to public DNS providers.
  
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

## Using the Service

* Using a web browser, go to the DNS name you registered and updated
  with the external endpoint.  You should be prompted to authenticate
  with GitHub, to choose an image from the menu (if that's how you set
  up your JupyterHub config), and then you should be redirected to your
  lab pod after selection.

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
