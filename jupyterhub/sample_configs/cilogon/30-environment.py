"""
Put all the sections together.
"""
import os

# Set up auth environment
c.LSSTAuth.oauth_callback_url = os.environ['OAUTH_CALLBACK_URL']
c.LSSTAuth.client_id = os.environ['OAUTH_CLIENT_ID']
c.LSSTAuth.client_secret = os.environ['OAUTH_CLIENT_SECRET']

ghowl = os.environ.get('GITHUB_ORGANIZATION_WHITELIST')
if ghowl:
    c.LSSTAuth.github_organization_whitelist = set(ghowl.split(","))

# Listen to all interfaces
c.JupyterHub.ip = '0.0.0.0'
c.Proxy.ip = '0.0.0.0'
# Don't try to cleanup servers on exit - since in general for k8s, we want
# the hub to be able to restart without losing user containers
c.JupyterHub.cleanup_servers = False
# Set Session DB URL if we have one
db_url = os.getenv('SESSION_DB_URL')
if db_url:
    c.JupyterHub.db_url = db_url
# Allow style overrides
c.JupyterHub.template_paths = ["/opt/lsst/software/jupyterhub/templates/"]

hub_route = os.environ.get('HUB_ROUTE')
if hub_route and hub_route != '/':
    c.JupyterHub.base_url = hub_route
