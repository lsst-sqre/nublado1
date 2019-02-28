"""
Put all the sections together.
"""
import os
from jupyter_client.localinterfaces import public_ips

# Set up auth environment
authtype = os.environ.get('OAUTH_PROVIDER') or ''
if authtype == 'jwt':
    # Parameters for JWT
    c.LSSTJWTAuth.signing_certificate = '/opt/jwt/signing-certificate.pem'
    c.LSSTJWTAuth.username_claim_field = 'uid'
    c.LSSTJWTAuth.expected_audience = os.getenv('OAUTH_CLIENT_ID') or ''
else:
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
k8s_svc_address = os.environ.get('HUB_SERVICE_HOST') or public_ips()[0]
c.JupyterHub.hub_connect_url = "http://" + k8s_svc_address + ":8081" + \
                               hub_route

# External proxy
c.ConfigurableHTTPProxy.should_start = False
proxy_host = os.getenv('PROXY_SERVICE_HOST') or '127.0.0.1'
proxy_port = os.getenv('PROXY_SERVICE_PORT_API') or '8001'
proxy_url = "http://" + proxy_host + ":" + proxy_port
c.ConfigurableHTTPProxy.api_url = proxy_url
