'''Runtime configuration for JupyterHub in the LSST environment.
'''

from jupyterhubutils import LSSTSpawner
from jupyterhubutils import LSSTCILogonOAuthenticator
from jupyterhubutils import LSSTGitHubOAuthenticator
from jupyterhubutils import LSSTJWTAuthenticator
from jupyterhubutils.lsstmgr.utils import (
    get_execution_namespace, make_logger, str_bool)
import os
from jupyter_client.localinterfaces import public_ips
from urllib.parse import urlparse

# This only works in the Hub configuration environment
c = get_config()

debug = (str_bool(os.getenv('DEBUG')) or False)
log = make_logger(debug=debug)
c.JupyterHub.spawner_class = LSSTSpawner


# Set up auth environment according to authtype
authtype = (os.environ.get('AUTH_PROVIDER') or
            os.environ.get('OAUTH_PROVIDER') or
            "github")
log.debug("Authentication type: {}".format(authtype))
if authtype == "github":
    c.Authenticator = LSSTGitHubOAuthenticator
elif authtype == "cilogon":
    c.Authenticator = LSSTCILogonOAuthenticator
elif authtype == "jwt":
    c.Authenticator = LSSTJWTAuthenticator
else:
    raise ValueError("Auth type '{}' not one of 'github'".format(authtype) +
                     ", 'cilogon', or 'jwt'!")

c.Authenticator.oauth_callback_url = os.environ['OAUTH_CALLBACK_URL']
netloc = urlparse(c.Authenticator.oauth_callback_url).netloc
scheme = urlparse(c.Authenticator.oauth_callback_url).scheme
aud = None
if netloc and scheme:
    aud = scheme + "://" + netloc
if authtype == 'jwt':
    # Parameters for JWT
    c.Authenticator.signing_certificate = '/opt/jwt/signing-certificate.pem'
    c.Authenticator.username_claim_field = 'uid'
    c.Authenticator.expected_audience = (
        aud or os.getenv('OAUTH_CLIENT_ID') or '')
else:
    c.Authenticator.client_id = os.environ['OAUTH_CLIENT_ID']
    c.Authenticator.client_secret = os.environ['OAUTH_CLIENT_SECRET']
if authtype == 'cilogon':
    c.Authenticator.scope = ['openid', 'org.cilogon.userinfo']
    skin = os.getenv("CILOGON_SKIN") or "LSST"
    c.Authenticator.skin = skin
    idp = os.getenv("CILOGON_IDP_SELECTION")
    if idp:
        c.Authenticator.idp = idp
if netloc:
    c.Authenticator.logout_url = netloc + "/oauth2/sign_in"


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
ns = get_execution_namespace()
log.debug("Namespace: {}".format(ns))
if ns:
    helm_tag = os.getenv("HELM_TAG")
    if helm_tag:
        hub = helm_tag + "-hub"
    else:
        hub = "hub"
    hub_svc_address = hub + "." + ns + ".svc.cluster.local"
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
