'''Runtime configuration for JupyterHub in the LSST environment.
'''

from jupyterhubutils import LSSTConfig, lsst_configure

# get_config() only works in the Hub configuration environment
c = get_config()

lc = LSSTConfig()
lsst_configure(lc)

# Set up the spawner
c.JupyterHub.spawner_class = lc.spawner_class

# Set up the authenticator
c.JupyterHub.authenticator_class = lc.authenticator_class

# Don't try to cleanup servers on exit - since in general for k8s, we want
# the hub to be able to restart without losing user containers
c.JupyterHub.cleanup_servers = False

# Set Session DB URL if we have one
db_url = lc.session_db_url
if db_url:
    c.JupyterHub.db_url = db_url
# Allow style overrides
c.JupyterHub.template_paths = ["/opt/lsst/software/jupyterhub/templates/"]

# Set Hub networking/routing parameters
hub_route = lc.hub_route
if hub_route != '/':
    c.JupyterHub.base_url = lc.hub_route

# Set the Hub URLs
c.JupyterHub.bind_url = lc.bind_url
c.JupyterHub.hub_bind_url = lc.hub_bind_url
c.JupyterHub.hub_connect_url = lc.hub_connect_url

# External proxy
c.ConfigurableHTTPProxy.should_start = False
c.ConfigurableHTTPProxy.api_url = lc.proxy_api_url
