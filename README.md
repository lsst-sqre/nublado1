# jupyterlabdemo

## Running

* Build a kubernetes evironment and log in with GitHub OAuth2.

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
  which is spawned on demand).  This is used to create a container (or
  multiple containers) for each component, in the following order.
  
### Fileserver

* This creates an auto-provisioned PersistentVolume by creating a
  PersistentVolumeClaim for the physical storage; then it
  stacks an NFS server atop that, adds a service for the NFS server, and
  then creates a (not namespaced) PersistentVolume representing the NFS
  export.  Then there is a (namespaced) PersistentVolumeClaim for the
  NFS export that the Lab pods will use.
  
* There is also a keepalive pod that just writes to the exported volume
  periodically.  Without it the NFS server will time out from inactivity
  eventually.

### Logstash

* The `filebeat` daemonset logs to a local `logstash` collector which
  uses RabbitMQ to send logs to a remote collector.  The name of the
  filebeat log, the target host, and the target port are described in
  deployment environment variables.

### Hub

* The Hub component has a Deployment and a Service.  It will need an
  actual URL assigned, although you won't get to that until the Nginx
  component.  On the Hub set up a GitHub application and environment
  variables as described at https://github.com/jupyterhub/oauthenticator .
  
#### Additional environment variables
  
* Additionally define the `GITHUB_ORGANIZATION_WHITELIST` environment
  variable with a comma-separated list of organizations whose members
  should be allowed to log in.
  
* Define `LAB_CONTAINER_NAMES` with the image names of the possible
  containers to spawn; it's also comma-separated.  If this is left
  undefined, the default image is `lsstsqre/jld-lab-py3`.
  
* `LAB_CONTAINER_DESCS` matches `LAB_CONTAINER_NAMES`: each
  (comma-separated) item corresponds to the image name in the same
  position in the list.
  
* `LAB_SELECTOR_TITLE` is a text string corresponding to the title text
  displayed above the image list.
  
* `LAB_CPU_LIMIT` corresponds to the number of CPUs a container is
  allowed.  The default is `1`.  Fractional CPUs can be defined in the
  form `0.2` or `200m`.
  
* `LAB_MEM_LIMIT` corresponds to the amount of memory a container is
  allowed to use.  The default is `2G`.
  
### Nginx

* Nginx terminates TLS and uses the Hub Service as its backend target.
  It too has a Deployment and a Service, and additionally the TLS
  secrets necessary for TLS termination.

### JupyterLab

* JupyterLab is launched from the Hub.  Each user gets a new pod, with a
  home directory on shared storage.  GitHub is the authentication
  source: the username is the GitHub user name, the UID is the GitHub ID
  number, and the groups are created with GIDs from the GitHub
  organizations the user is a member of, and their IDs.

## Particular versions

* JupyterHub 396f4549989f593c91bfed0e9255229d48ea2ada
* * Plus:
* JupyterLab 575fed6cf8c6219fc0b711e728c8fae4ea5b6edd

JupyterHub needs the following replacement in
`jupyterhub/jupyterhub/handlers/base.py`:

```python
    def user_from_username(self, nameobj):
        """Get User for username, creating if it doesn't exist"""
        if type(nameobj) is dict:
            username = nameobj["name"]
        else:
            username = nameobj  # This will explode if it's not a string
        user = self.find_user(username)
        if user is None:
            # not found, create and register user
            u = orm.User(name=username)
            self.db.add(u)
            self.db.commit()
            user = self._user_from_orm(u)
            self.authenticator.add_user(user)
        return user
```
