"""
Put all the sections together.
"""
import os
from jupyter_client.localinterfaces import public_ips
from urllib.parse import urlparse


def _get_namespace():
    ns_path = '/var/run/secrets/kubernetes.io/serviceaccount/namespace'
    if os.path.exists(ns_path):
        with open(ns_path) as f:
            return f.read().strip()
    return None


# Set up auth environment
authtype = os.environ.get('OAUTH_PROVIDER') or "github"

c.LSSTAuth = c.LSSTGitHubAuth
if authtype == "cilogon":
    c.LSSTAuth = c.LSSTCILogonAuth
elif authtype == "jwt":
    c.LSSTAuth = c.LSSTJWTAuth
    c.LSSTAuth.auth_refresh_age = 900

c.LSSTAuth.oauth_callback_url = os.environ['OAUTH_CALLBACK_URL']
netloc = urlparse(c.LSSTAuth.oauth_callback_url).netloc
scheme = urlparse(c.LSSTAuth.oauth_callback_url).scheme
aud = None
if netloc and scheme:
    aud = scheme + "://" + netloc
if authtype == 'jwt':
    # Parameters for JWT
    c.LSSTJWTAuth.signing_certificate = '/opt/jwt/signing-certificate.pem'
    c.LSSTJWTAuth.username_claim_field = 'uid'
    c.LSSTJWTAuth.expected_audience = (aud or
                                       os.getenv('OAUTH_CLIENT_ID') or '')
    if netloc:
        c.JupyterHub.logout_url = netloc + "/oauth2/sign_in"
else:
    c.LSSTAuth.client_id = os.environ['OAUTH_CLIENT_ID']
    c.LSSTAuth.client_secret = os.environ['OAUTH_CLIENT_SECRET']

ghowl = os.environ.get('GITHUB_ORGANIZATION_WHITELIST')
if ghowl:
    c.LSSTGitHubAuth.github_organization_whitelist = set(ghowl.split(","))

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
ns = _get_namespace()
if ns:
    hub_svc_address = "hub." + ns + ".svc.cluster.local"
else:
    hub_svc_address = os.environ.get('HUB_SERVICE_HOST') or public_ips()[0]
hub_api_port = os.environ.get('HUB_SERVICE_PORT_API') or '8081'
c.JupyterHub.hub_connect_url = "http://{}:{}{}".format(hub_svc_address,
                                                       hub_api_port,
                                                       hub_route)

# External proxy
c.ConfigurableHTTPProxy.should_start = False
proxy_host = os.getenv('PROXY_SERVICE_HOST') or '127.0.0.1'
proxy_port = os.getenv('PROXY_SERVICE_PORT_API') or '8001'
proxy_url = "http://" + proxy_host + ":" + proxy_port
c.ConfigurableHTTPProxy.api_url = proxy_url

# Skin and restricted IDP for CILogon
c.LSSTCILogonAuth.scope = ['openid', 'org.cilogon.userinfo']
skin = os.getenv("CILOGON_SKIN") or "LSST"
c.LSSTCILogonAuth.skin = skin
idp = os.getenv("CILOGON_IDP_SELECTION")
if idp:
    c.LSSTCILogonAuth.idp = idp
