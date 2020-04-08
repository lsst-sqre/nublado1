'''Runtime configuration for JupyterHub in the LSST environment.
'''

import jupyterhubutils
import logging
from eliot.stdlib import EliotHandler
from jupyterhubutils import LSSTConfig
from jupyterhubutils.utils import make_logger

# get_config() only works in the Hub configuration environment
c = get_config()

lc = LSSTConfig()
# Set logging
c.Application.log_format = lc.log_format
c.Application.log_datefmt = lc.log_datefmt
c.Application.log_level = lc.log_level
c.Application.log = make_logger(name='JupyterHub')
c.Application.log.handlers = [EliotHandler()]

jupyterhubutils.configure_auth_and_spawner(lc)
jhu_logger = make_logger(name='jupyterhubutils')
if lc.debug:
    jhu_logger.setLevel(logging.DEBUG)
    jhu_logger.debug("Enabling 'jupyterhubutils' debug-level logging.")
    jhu_logger.warning("If there's not a prior debug log something is wrong.")

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
