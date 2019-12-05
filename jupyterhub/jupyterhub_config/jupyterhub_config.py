'''Runtime configuration for JupyterHub in the LSST environment.
'''

from jupyterhubutils import LSSTSpawner
from jupyterhubutils.config_helpers import (get_authenticator_class,
                                            configure_authenticator,
                                            get_db_url, get_hub_parameters,
                                            get_proxy_url)

# This only works in the Hub configuration environment
c = get_config()

# Set up the spawner
c.JupyterHub.spawner_class = LSSTSpawner

# Set up the authenticator
c.JupyterHub.authenticator_class = get_authenticator_class()
configure_authenticator()

# Don't try to cleanup servers on exit - since in general for k8s, we want
# the hub to be able to restart without losing user containers
c.JupyterHub.cleanup_servers = False

# Set Session DB URL if we have one
db_url = get_db_url()
if db_url:
    c.JupyterHub.db_url = db_url
# Allow style overrides
c.JupyterHub.template_paths = ["/opt/lsst/software/jupyterhub/templates/"]

# Set Hub networking/routing parameters
hub_api_parms = get_hub_parameters()
hub_route = hub_api_parms["route"]
hub_svc_address = hub_api_parms["svc"]
hub_api_port = hub_api_parms["port"]
if hub_route != '/':
    c.JupyterHub.base_url = hub_route

# Set the Hub URLs
c.JupyterHub.bind_url = 'http://0.0.0.0:8000' + hub_route
c.JupyterHub.hub_bind_url = 'http://0.0.0.0:8081' + hub_route
c.JupyterHub.hub_connect_url = "http://{}:{}{}".format(hub_svc_address,
                                                       hub_api_port,
                                                       hub_route)

# External proxy
c.ConfigurableHTTPProxy.should_start = False
c.ConfigurableHTTPProxy.api_url = get_proxy_url()
