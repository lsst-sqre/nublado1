# Manual Deployment of the LSST Science Platform Notebook Aspect

If you are here, consider one of the more automated deployment methods:
[Terraform](terraform/README.md) or the [Deployment Tool](README.md).

## Deploying the LSST Science Platform Notebook Aspect

### Requirements
 
* Begin by cloning this repository: `git clone
  https://github.com/lsst-sqre/nublado`.  You will be working
  with the kubernetes deployment files inside it, so it will probably be
  convenient to `cd` inside it.

* You will need `kubectl` installed in order to run the Kubernetes
  commands throughout these instructions.  In order to deploy the
  landing page, which uses a binary ConfigMap for its content, you will
  need version `1.10` or later of `kubectl`.

* You need to start with a cluster to which you have administrative
  access.  This is created out-of-band at this point, using whatever
  tools your Kubernetes administrative interface gives you.  Use
  `kubectl config use-context <context-name>` to set the default
  context.  In order to use the landing page, the cluster's master and
  node Kubernetes versions must be at least `1.10`.

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
  will be the endpoint of the Science Platform instance.  This too is
  necessary for OAuth to work.  Create it with a short TTL and a bogus
  address (I recommend `127.0.0.1`); you will update the address once
  the exposed IP endpoint of the Jupyter cluster is known.

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
  appends `/nb/hub/oauth_callback` to that.

* These instructions and templates generally assume Google Container
  Engine.  If you are using a different Kubernetes provider, you will
  need to adjust your processes to fit in some cases; for instance,
  auto-provisioning a PersistentVolume when presented with an
  unsatisfied PersistentVolumeClaim is a Google feature.

### Component Structure

* Each LSST Science Platform Notebook Aspect component has a
  `kubernetes` directory (except for JupyterLab, which is spawned on
  demand).  The files in this directory are used to create the needed
  pods for the corresponding services.

* The next sections provide an ordered list of services to deploy in the
  cluster.

* Anywhere there is a template file (denoted with `.template.yml` as the
  end of the filename), it should have the template variables (denoted
  with double curly brackets, e.g. `{{HOSTNAME}}`) substituted with a
  value before use.

### Creating secrets

* In general, secrets are stored as base64-encoded strings within
  `secrets.yml` files.  The incantation to create a secret is 
  `echo -n <secret> | base64 -i -`.  The `-n` is necessary to prevent
  a newline from being encoded at the end.

* For secrets created from files (e.g. TLS certificates), the
  incantation is `base64 <secret_filename> | tr -d '\n'` to emit the
  base64 representation of the file as a single string without
  linebreaks.

### Nginx Ingress Controller

* The Ingress Controller components are found in the `nginx-ingress`
  directory.  The controller will live in its own namespace.
  
* Create the namespace first, with `kubectl create -f
  ingress-nginx-namespace.yml`.  Then create, in order:
    * `default-http-backend-deployment`
    * `default-http-backend-service`
    * `nginx-configuration-configmap`
    * `tcp-services-configmap`
    * `udp-services-configmap`
    * `nginx-ingress-serviceaccount`
    * `nginx-ingress-clusterrolebinding`
    * `nginx-ingress-clusterrole`
    * `nginx-ingress-role`
    * `nginx-ingress-rolebinding`
    * `nginx-ingress-controller-deployment`
    * `ingress-nginx-service`

* Once the service has been created, wait until it brings up an external
  IP address: `kubectl get svc -n ingress-nginx ingress-nginx` and
  inspect the `EXTERNAL-IP` field, or `N="ingress-nginx" kubectl get svc
  ${N} -n ${N} | grep ${N} | awk '{print $4}'`.  Then update your DNS
  record for the external endpoint with this IP address.

### TLS

* Create secrets from the secrets template.  The three standard TLS
  files should be the CA certificate, the key, and the server
  certificate, all base64-encoded and put into the file.  `dhparam.pem`
  can be created with `openssl dhparam -out dhparam.pem 2048`, and then
  base64-encoded and inserted into the secrets YAML file.  That command
  may take some time to run.

### Logging [optional]

* The logging components are located in the `logstashrmq` and `filebeat`
  directories within the repository.

* The logging architecture is as follows: `filebeat` runs as a daemonset
  (that is, exactly one container per node), and scrapes the docker logs
  from the host filesystem mounted into the container.  It sends those
  to a `logstash` container in the same cluster, which transmits the
  logs via RabbitMQ to a remote ELK stack.

* Start with `logstashrmq`.  Copy the `secrets.template.yml`
  file, and paste the base64 encoding of your rabbitmq password into
  the appropriate field (in place of `{{RABBITMQ_PAN_PASSWORD}}`, then
  `kubectl create -f secrets.yml` (assuming that's what you named your
  secrets file).  This is going to be a frequently-repeated
  pattern for updating secrets (and occasionally other deployment files)
  from templates.

* Create the service next with `kubectl create -f service.yml`.
  Kubernetes services simply provide fixed (within the cluster) virtual
  IP/port combinations that abstract away from the particular deployment
  pod, so you can replace the implementation without your other
  components having to care.
  
* Copy the `deployment.template.yml` file, replace the template fields
  with your RabbitMQ target host and Vhost (top-level exchange), and
  create the service with `kubectl -f deployment.yml`.

* Next go to `filebeat`.  Add the base64-encodings of your three TLS
  files (the CA, the certificate, and the key) to a copy of
  `secrets.template.yml`.  Create those secrets.  Copy the deployment
  template, replace the placeholder (`SHIPPER_NAME` is an arbitrary
  string so that you can find these logs on your collecting system;
  usually the cluster name is a good choice), and create the DaemonSet
  from your template-substituted file.
  
* At this point every container in your cluster will be logging to your
  remote ELK stack.

### Fileserver

* The fileserver is located in the `fileserver` directory.

* This creates an auto-provisioned PersistentVolume by creating a
  PersistentVolumeClaim for the physical storage; then it
  stacks an NFS server atop that and adds a service for the NFS server.
  
* There is also a keepalive pod that just writes to the exported volume
  periodically.  Without it the NFS server will time out from inactivity
  eventually.

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

`kubectl create -f storageclass.yml`

(the `pd-ssd` type parameter is what does that for you; this may be
Google Kubernetes Engine-specific)

#### NFS Service

Create a service to expose the NFS server (only inside the cluster)
with the following:

`kubectl create -f service.yml`

You will need the IP address of the service for a subsequent step.
`kubectl describe service fileserver` and note the IP address.
Alternatively, `kubectl describe service fileserver | grep ^IP: |
awk '{print $2}'` to get just the IP address.

##### Physical Storage PersistentVolumeClaim

Next, create a PersistentVolumeClaim (*not* a PersistentVolume!) for the
underlying storage.  Copy the template file
`physpvc.template.yml` to a working file.  Substitute the
disk size in the `storage` field (GKE has a default quota of 500GB);
the size depends on how much local storage you expect your users to
require.

`kubectl create -f physpvc.yml`

On Google Kubernetes Engine, this will automagically create a
PersistentVolume to back it.  I, at least, found this very surprising.

If you are not running under GKE you will need to create a
PersistentVolume for the PersistentVolumeClaim to bind.

Note that our default deployment puts all exported volumes on a single
physical volume.  You can modify the deployment to put any or all of
`home`, `scratch`, `project`, `datasets`, `software`, and `teststand` as
separate physical volumes which you then export.  In the real LDF
environment they are of course separate volumes managed from an external
file server.

#### NFS v4 Server [not necessarily in kubernetes]

If you are already in an environment where there is an available NFS
server, then you can omit actually providing your own NFS implementation
in this step and the next and simply point to the external NFS service.

The next step is to create an NFS v4 Server that serves up the actual
disk.

`kubectl create -f deployment.yml`

I created my own NFS Server image.  You could probably just use Google's
image and it'd be fine.

### NFS Keepalive Service

* This service lives in `fs-keepalive`.

* All it does is periodically write a record to the writeable
  NFS-mounted filesystems, which insures that the fileserver doesn't get
  descheduled when idle.
  
* Create it with `kubectl create -f deployment.yml`

### Firefly [optional]

* The Firefly server is a multi-user server developed by IPAC at
  Caltech.  This component, located in `firefly`, provides a multi-user
  server within the Kubernetes cluster.

* Create secrets from the template by copying
  `firefly-secrets.template.yml` to a working file, and then
  base64-encode and adding an admin password in place of
  `{{FIREFLY_ADMIN_PASSWORD}}`.
  
* Make a copy of `firefly-deployment-template.yml`.  Set
  `FIREFLY_REPLICAS`, `FIREFLY_CONTAINER_MEM_LIMIT`, and
  `FIREFLY_MAX_JVM_SIZE`.  The maximum JVM size should be slightly
  smaller than the container memory limit.  Create the deployment with
  `kubectl create -f` against your working file.

* Copy `firefly-ingress.template.yml` to a working file, substituting
  `FIREFLY_ROUTE` (use `/firefly/` if you have no particular reason to do
  otherwise) and `HOSTNAME`.  Create that with `kubectl -f` against the
  working file.

* Create the service with `kubectl create -f` against the appropriate
  YAML files.  Firefly will be available at whatever you set
  `FIREFLY_ROUTE` to (probably `/firefly/`).

### Prepuller [optional]

* Prepuller is very much geared to the LSST Science Platform use case.
  It is only needed because our containers are on the order of 10GB each;
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
      Experimental/Daily/Weekly/Release images to prepull.
	  
* After creating the working file (let's assume you called it
  `prepuller-cronjob.yml)`, run  `kubectl create -f prepuller-cronjob.yml`.

### JupyterHub

This is the most complex piece, and is the one that requires the most
customization on your part.

* This is located in `jupyterhub`.

* Start by creating the `service` component.

* Create a service account for `jupyterhub` so that it can manipulate
  pods using Role-Based Access Control: `kubectl create -f
  serviceaccount.yml`.
  
* Create a ClusterRole (the Hub needs the ability to manipulate
  namespaces and pods and quotas in multiple namespaces): `kubectl
  create -f clusterrole.yml`.
  
* Create a ClusterRoleBinding by copying
  `clusterrolebinding.template.yml` to a working file,
  substituting the namespace.  Create it with `kubectl -f` run against
  the working file.

* Next, create the Persistent Volume Claim: `kubectl create -f
  physpvc.yml`.  The Hub needs some persistent storage so its
  knowledge of user sessions survives a container restart.

* Create a file from the secrets template.  Populate this secrets file
  with the following (base64-encoded):
  
  1. The `Client ID`, `Client Secret`, and `Callback URL` from the
     OAuth2 Application you registered with GitHub at the beginning.  If
     you are using JWT authentication you can leave these empty.
  2. `github_organization_whitelist` is a comma-separated list of the
     names of the GitHub organizations whose members will be allowed to
     log in.  Either membership in the organization must be public, or
     the scopes requested for the OAuth2 token must include `read:org`
     in order for users to be able to log in based on the whitelist.
	 The secrets `github_organization_denylist` is the dual of this:
	 no members of this organization may log in.  The pair
	 `cilogon_organization_whitelist` and
     `cilogon_organization_denylist` are similar; any unneeded values
	 may be set to the empty string.
  3. `session_db_url`.  If you don't know this or are happy with the
     stock sqlite3 implementation, use the URL
     `sqlite:////home/jovyan/jupyterhub.sqlite`; any RDBMS supported by
     SQLAlchemy can be used.
  4. `jupyterhub_crypto_key`; I use `openssl rand -hex 32` to get 16
     random bytes.  I use two of these separated by a semicolon as the
     secret, and the reason for that is that I can simply implement key
     rotation by, every month or so, dropping the first key, moving the
     second key to the first position, and generating a new key for the
     second position.  The command `"r="openssl rand -hex 32"; echo
     "$(${r});$(${r})"` will generate a pair in this form for you.
  5. `configproxy_auth_token`; use `openssl rand -hex 32` to get 16 more
     random bytes.  The Configurable HTTP Proxy does not have facilities
	 for key rotation.

  Once you have done that, create the secrets from the file: `kubectl
  create -f <filename>`.
  
* Set up your deployment environment by editing the environment
  variables in `deployment.yml`.

  1. Set the environment variable `OAUTH_PROVIDER` to one of `github`,
    `cilogon`, or `jwt` depending on which provider you want to use.

  2. Set the environment variable
    `K8S_CONTEXT` to the context in which your deployment is running
    (`kubectl config current-context` will give you that information).
	
  3. If you changed the namespace, put the current namespace in the
     environment variable `K8S_NAMESPACE`.
	 
  4. If you have a repository containing a container image with multiple
     tags you wish to present as container options, you should set
     `LAB_SELECTOR_TITLE` to the title of the spawner options form,
     `LAB_REPO_HOST` to the hostname of the Docker container repository,
     `LAB_OWNER` to the name of the repository owner, and
     `LAB_REPO_NAME` to the name of the image.  The container name will
     then be `LAB_REPO_HOST`/`LAB_OWNER`/`LAB_REPO_NAME`.  If you only
     have a single image, set `LAB_IMAGE` to that container name.  It
     will default to `lsstsqre/sciplat-lab:latest` (with
     `hub.docker.com` as the implied repository host).
	 
   5. If you want to allow users to spawn dask nodes, set
      `ALLOW_DASK_SPAWN` to a non-empty value.  If you want to restrict
      dask and Lab containers to particular nodes, set
      `RESTRICT_DASK_NODES` and/or `RESTRICT_LAB_NODES`.  That will only
      allow containers of each type to spawn where the node has the
      Kubernetes label `dask` or `jupyterlab` with a value of `ok`.
      Labelling the nodes is not currently part of the deployment
      process.

* Edit the configuration in `jupyterhub_config/jupyterhub_config.d` if
  you want to.
  - The files in the configuration directory are sourced in lexical sort
    order; typically they are named with a two-digit priority as a
    prefix.  Lower numbers are loaded first.
  - In the GitHub authenticator, we subclass GitHubOAuthenticator to set
    container properties from our environment and, crucially, from
    additional properties (GitHub organization membership and email
    address) we can access from the token-with-additional-scope.  The
    extended scope is configured at the bottom, as a configuration
    setting on our authenticator class.
  - If you're using CILogon, the setup is quite similar; scope, the
    authenticator skin, and the identity provider to use are all set as
    configurable properties of the authenticator class.
  - Which of the GitHub, CILogon, or JWT authenticator classes to use is
    determined by the value of the `OAUTH_PROVIDER` environment
    variable.
  - In the spawner class, we subclass NamespacedKubeSpawner to build a
    dynamic list of kernels (current as of user login time) and then do
    additional launch-time setup, to spawn the user pod into a
    user-specific namespace.

* If you are using `jwt` as your authentication type, copy the public
  key from the JWT implementation's signing certificate over
  `jupyterhub_config/signing-certificate.pem`.

* Deploy the file using the `redeploy` script, which will create
  the `ConfigMap` resource from the JupyterHub configuration, and then
  deploy the Hub into the specified context and namespace.

### Configurable HTTP Proxy

* The Configurable HTTP Proxy is a Jupyter-provided piece that manages
  per-user routes to spawned Lab servers.

* This is located in `proxy`.

* Create the service with `kubectl -f service.yml`.

* Create the deployment with `kubectl -f deployment.yml`.

* Copy `ingress.template.yml` to a working file, substituting
  `HUB_ROUTE` (use `/nb/` if you have no particular reason to do otherwise)
  and `HOSTNAME`.  If you are using `jwt` authentication, uncomment the
  indicated lines and ensure that MAX_HTTP_HEADER_SIZE is at least
  16384. Create the resource with `kubectl -f` against the
  working file.

### Landing Page (optional)

If the route to the Hub is not `/` you will probably want a landing
page.  Specifically, to mimic the LSP site, the Hub route should be
`/nb/` and you should use a landing page.

* This is located in `landing-page`.

* Create the associated service with `kubectl create -f
  landing-page-service.yml`.

* Copy `landing-page-ingress.template.yml` to a working file, replace
  `{{HOSTNAME}}` with your FQDN, and create the ingress with `kubectl
  create -f` against the working file.
  
* Create the ConfigMap that contains the landing page files: `kubectl
  create configmap landing-page-www --from-file=config/`.  Note that
  this requires Kubernetes `1.10` or later and a matching `kubectl`.
  
* Create the deployment with `kubectl create -f
  landing-page-deployment.yml`.
  
### JupyterLab

JupyterLab is launched from the Hub.

* Each user gets a new pod, with a home directory on shared storage, in
  a namespace unique to that user.

* With GitHub as the authentication source, the username is the GitHub
  user name, the UID is the GitHub ID number, and the groups are created
  with GIDs from the GitHub organizations the user is a member of, and
  their IDs.

* Git will be preconfigured with a token that allows authenticated
  HTTPS pushes, and with the user's name and primary email, assuming
  that the GitHub authenticator is in use.

## Using the Service

* Using a web browser, go to the DNS name you registered and updated
  with the external endpoint.  You should be prompted to authenticate
  with GitHub, to choose an image from the menu (if that's how you set
  up your JupyterHub config), and then you should be redirected to your
  lab pod after selection.

## Building

* Each component that is unique to the LSST Science Platform Notebook
  Aspect has a `Dockerfile`.  `./bld` in its directory will build the
  container.  Unless you're in the lsstsqre Docker organization, you're
  going to need to change the container name label.
  
* The `bld` script requires that the description, name, and version
  labels be on separate lines.  The poor thing's not very bright.
 
* You probably don't need to rebuild anything.  If you do, it's because
  I have not made something sufficiently configurable, so I'd appreciate
  hearing about it.
