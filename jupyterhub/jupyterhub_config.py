# This is the JupyterHub configuration file LSST DM-SQuaRE uses.

# It spawns JupyterLab containers and does its authentication using
#  GitHub organization membership (and on the Lab pods, it does some magic
#  to set the UID equal to the GitHub ID and GIDs that match orgs).

# If it doesn't work for you, replace it in your Kubernetes config.
# It's mapped in as a configmap.  Look at the deployment file:
# jld-hub-config/jld-hub-cfg.py ->
#  /opt/lsst/software/jupyterhub/config/jupyterhub_config.py

# GitHub Org Whitelist authenticator.
import ghowlauth
c.JupyterHub.authenticator_class = 'ghowlauth.GHOWLAuthenticator'

# Now that this whole thing is a ConfigMap, it's slightly silly to be
#  worrying about the environment substitution here, but you can get
#  quite a long way with just environment variables.

import os
c.GHOWLAuthenticator.oauth_callback_url = os.environ['OAUTH_CALLBACK_URL']
c.GHOWLOAuthenticator.client_id = os.environ['GITHUB_CLIENT_ID']
c.GHOWLOAuthenticator.client_secret = os.environ['GITHUB_CLIENT_SECRET']

import sqrekubespawner
c.JupyterHub.spawner_class = 'sqrekubespawner.SQREKubeSpawner'

c.JupyterHub.ip = '0.0.0.0'

# Don't try to cleanup servers on exit - since in general for k8s, we want
# the hub to be able to restart without losing user containers
c.JupyterHub.cleanup_servers = False

# First pulls can be really slow for the LSST stack containers,
#  so let's give it a big timeout
c.SQREKubeSpawner.http_timeout = 60 * 15
c.SQREKubeSpawner.start_timeout = 60 * 15

# The spawned containers need to be able to talk to the hub through the proxy!
c.SQREKubeSpawner.hub_connect_port = int(os.environ['JLD_HUB_SERVICE_PORT'])
c.SQREKubeSpawner.hub_connect_ip = os.environ['JLD_HUB_SERVICE_HOST']
c.JupyterHub.hub_ip = os.environ['HUB_BIND_IP']

# Set up memory and CPU upper/lower bounds
memlim = os.getenv('LAB_MEM_LIMIT')
if not memlim:
    memlim = '2G'
memguar = os.getenv('LAB_MEM_GUARANTEE')
if not memguar:
    memguar = '0K'
cpulimstr = os.getenv('LAB_CPU_LIMIT')
cpulim = 1.0
if cpulimstr:
    cpulim = float(cpulimstr)
cpuguar = 0.0
cpuguarstr = os.getenv('LAB_CPU_GUARANTEE')
if cpuguarstr:
    cpugaur = float(gpuguarstr)
c.SQREKubeSpawner.mem_limit = memlim
c.SQREKubeSpawner.cpu_limit = cpulim
c.SQREKubeSpawner.mem_guarantee = memguar
c.SQREKubeSpawner.cpu_guarantee = cpuguar

# We are running the Lab at the far end, not the old Notebook
c.SQREKubeSpawner.default_url = '/lab'

# Persistent shared user volume
c.SQREKubeSpawner.volumes = [
    {"name": "jld-fileserver-home",
     "persistentVolumeClaim": {"claimName": "jld-fileserver-home"}}]
c.SQREKubeSpawner.volume_mounts = [
    {"mountPath": "/home",
     "name": "jld-fileserver-home"}]

# Let us set the images from the environment.
c.SQREKubeSpawner.singleuser_image_pull_policy = 'Always'
# Get (possibly list of) image(s)
imgspec = os.getenv("LAB_CONTAINER_NAMES")
if not imgspec:
    imgspec = "lsstsqre/jld-lab-py3:latest"
imagelist = imgspec.split(',')
if len(imagelist) < 2:
    c.SQREKubeSpawner.singleuser_image_spec = imgspec
else:
    title = os.getenv("LAB_SELECTOR_TITLE")
    if not title:
        title = "Container Image Selector"
    idescstr = os.getenv("LAB_CONTAINER_DESCS")
    if not idescstr:
        idesc = imagelist
    else:
        idesc = idescstr.split(',')
    # Build the options form.
    optform = "<label for=\"%s\">%s</label></br>\n" % (title, title)
    for idx, img in enumerate(imagelist):
        optform += "      "
        optform += "<input type=\"radio\" name=\"lsst_stack\""
        try:
            imgdesc = idesc[idx]
        except IndexError:
            imgdesc = img
        if not imgdesc:
            imgdesc = img
        optform += " value=\"%s\">%s<br>\n" % (img, imgdesc)
    # Options form built.
    c.SQREKubeSpawner.options_form = optform

db_url = os.getenv('SESSION_DB_URL')
if db_url:
    c.JupyterHub.db_url = db_url
