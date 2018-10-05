"""
Put all the sections together.
"""
import os
from jupyter_client.localinterfaces import public_ips

# Set up auth environment
c.LSSTAuth.oauth_callback_url = os.environ['OAUTH_CALLBACK_URL']
c.LSSTAuth.client_id = os.environ['OAUTH_CLIENT_ID']
c.LSSTAuth.client_secret = os.environ['OAUTH_CLIENT_SECRET']

ghowl = os.environ.get('GITHUB_ORGANIZATION_WHITELIST')
if ghowl:
    c.LSSTAuth.github_organization_whitelist = set(ghowl.split(","))

# Don't try to cleanup servers on exit - since in general for k8s, we want
# the hub to be able to restart without losing user containers
c.JupyterHub.cleanup_servers = False
# Set Session DB URL if we have one
db_url = os.getenv('SESSION_DB_URL')
if db_url:
    c.JupyterHub.db_url = db_url
# Allow style overrides
c.JupyterHub.template_paths = ["/opt/lsst/software/jupyterhub/templates/"]

hub_route = os.environ.get('HUB_ROUTE') or "/"
if hub_route != '/':
    c.JupyterHub.base_url = hub_route

# Set the Hub URLs
c.JupyterHub.bind_url = 'http://0.0.0.0:8000' + hub_route
c.JupyterHub.hub_bind_url = 'http://0.0.0.0:8081' + hub_route
k8s_svc_address = os.environ.get('JLD_HUB_SERVICE_HOST') or public_ips()[0]
c.JupyterHub.hub_connect_url = "http://" + k8s_svc_address + ":8081" + \
                               hub_route
# Add node selector
if os.getenv('RESTRICT_LAB_NODES'):
    c.KubeSpawner.node_selector.update({'jupyterlab': 'ok'})
