# Rubin Observatory Science Platform Notebook Aspect

## You Probably Should Not Use This

If what you want to do is simply deploy a Jupyter setup under Kubernetes
you're much better off
using
[Zero to JupyterHub](https://zero-to-jupyterhub.readthedocs.io/en/latest/),
which is an excellent general tutorial for setting up JupyterHub in a
Kubernetes environment.

This cluster is much more specifically tailored to the needs of
the [Rubin Observatory](https://rubinobservatory.org).  If you want an
example of how to set up persistent storage for your users, a worked
example of how to subclass a spawner or authenticator, or how to use a
custom image-spawner options menu, you may find it useful.

## Overview

The Rubin Observatory Science Platform Notebook Aspect is a JupyterHub +
JupyterLab environment that runs in a Kubernetes cluster.  It provides
JWT authentication via
the [Gafaelfawr](https://github.com/lsst-sqre/gafaelfawr) service, which
can use CILogon or GitHub as its backend.  It also provides a JupyterHub
portal and spawned-on-demand JupyterLab containers.  It can also
include, (optionally) an image prepuller to speed startup even in an
environment with heavy Lab image churn, an IPAC Firefly server, and a
mechanism to allow dask nodes for parallel computing.

### Using the Rubin Observatory Data Management Science Stack

#### Notebook

* Choose `LSST` as your Python kernel.  Then you can `import lsst`
  and the stack and all its pre-reqs are available in the environment.
  
#### Terminal

* Start by running `. /opt/lsst/software/stack/loadLSST.bash`.  Then
  `setup lsst_distrib` and then you're in a shell environment with the
  stack available.

## Deploying an LSST Science Platform Notebook Aspect Kubernetes Cluster

### Helm

There are Helm charts available at https://github.com/lsst-sqre/charts
in the `nublado` directory.  We deploy with Argo CD, and our
site-specific values are held in the `services/nublado` directory of
https://github.com/lsst-sqre/lsp-deploy .
