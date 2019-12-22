# LSST Science Platform Notebook Aspect

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

The LSST Science Platform Notebook Aspect is a JupyterHub + JupyterLab
environment that runs in a Kubernetes cluster.  It provides GitHub or
CILogon OAuth2 authentication, authorization via GitHub organization
membership or (with the NCSA identity provider) CILogon group
membership, a JupyterHub portal, and spawned-on-demand JupyterLab
containers.  It can also, optionally, include a filebeat configuration
to log to a remote ELK stack, an image prepuller to speed startup even
in an environment with heavy Lab image churn, an IPAC Firefly server,
and a mechanism to allow dask nodes for parallel computing.

## Running

* Log in with GitHub OAuth2.  You must be a member of one of the
  organizations listed in the GitHub Organization Whitelist, and either
  your membership in that organization must be `public` rather than
  `private`, or `read:org` must be among the scopes granted by the
  OAuth token.

* While the code supports CILogon with the NCSA identity provider (and
  an OAuth2 proxy there that yields a JWT we use for authentication),
  our assumption is that if that's what you want to do, NCSA is managing
  the kubernetes cluster for you and installation instructions are thus
  irrelevant to you.

### Using the LSST Stack

#### Notebook

* Choose `LSST` as your Python kernel.  Then you can `import lsst`
  and the stack and all its pre-reqs are available in the environment.
  
#### Terminal

* Start by running `. /opt/lsst/software/stack/loadLSST.bash`.  Then
  `setup lsst_distrib` and then you're in a stack shell environment.

## Deploying an LSST Science Platform Notebook Aspect Kubernetes Cluster

### Helm

There are Helm charts available at https://github.com/lsst-sqre/charts
in the `nublado` directory.  We deploy with Argo CD, and our
site-specific values are held in the `services/nublado` directory of
https://github.com/lsst-sqre/lsp-deploy .
