# jupyterlabdemo

## Running

* `docker run -it --rm -p 8000:8000 --name jupyterlabdemo
  lsstsqre/jupyterlabdemo`

* You can log in with local (PAM) authentication.

### Notebook

* Choose `LSST_Stack` as your Python kernel.  Then you can `import lsst`
  and the stack and all its pre-reqs are available in the environment.
  
### Terminal

* Start by running `. /opt/lsst/software/stack/loadLSST.bash`.  Then
  `setup lsst_distrib` and then you're in a stack shell environment.

## Building

* `docker build -t lsstsqre/jupyterlabdemo .`

## Kubernetes

* The files in the `kubernetes` directory create a pod and service for
  jupyterlabdemo.  It's intended to run behind SSL termination at a
  reverse proxy; we're using
  https://github.com/lsst-sqre/k8s-jupyterlabdemo-nginx for that
  purpose.

* Put it behind an actual URL, and set up a GitHub application and
  environment variables as described at
  https://github.com/jupyterhub/oauthenticator 
  
* Additionally define the GITHUB_ORGANIZATION_WHITELIST environment
  variable with a comma-separated list of organizations whose members
  should be allowed to log in.

