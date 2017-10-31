"""
This authenticator uses GitHub organization membership to make authentication
and authorization decisions.
"""
import json
import os
import oauthenticator
from oauthenticator.common import next_page_from_links
from tornado import gen
from tornado.httpclient import HTTPRequest, AsyncHTTPClient, HTTPError


# Utility definitions from GitHub OAuthenticator.

# Support github.com and github enterprise installations
GITHUB_HOST = os.environ.get('GITHUB_HOST') or 'github.com'
if GITHUB_HOST == 'github.com':
    GITHUB_API = 'api.github.com'
else:
    GITHUB_API = '%s/api/v3' % GITHUB_HOST


def _api_headers(access_token):
    return {"Accept": "application/json",
            "User-Agent": "JupyterHub",
            "Authorization": "token {}".format(access_token)
            }


# Request additional scope on GitHub token to auto-provision magic in the
# user container.
class LSSTLoginHandler(oauthenticator.GitHubLoginHandler):
    """Request additional scope on GitHub token.
    """
    scope = ['public_repo', 'read:org', 'user:email']


# Enable the authenticator to spawn with additional information acquired
# with token with larger-than-default scope.
class LSSTAuth(oauthenticator.GitHubOAuthenticator):
    """Authenticator to use our custom environment settings.
    """
    enable_auth_state = True

    _state = None

    login_handler = LSSTLoginHandler

    @gen.coroutine
    def pre_spawn_start(self, user, spawner):
        # First pulls can be really slow for the LSST stack containers,
        #  so let's give it a big timeout
        spawner.http_timeout = 60 * 15
        spawner.start_timeout = 60 * 15
        # The spawned containers need to be able to talk to the hub through
        #  the proxy!
        spawner.hub_connect_port = int(os.environ['JLD_HUB_SERVICE_PORT'])
        spawner.hub_connect_ip = os.environ['JLD_HUB_SERVICE_HOST']
        # Set up memory and CPU upper/lower bounds
        memlim = os.getenv('LAB_MEM_LIMIT')
        if not memlim:
            memlim = '2G'
        memguar = os.getenv('LAB_MEM_GUARANTEE')
        if not memguar:
            memguar = '64K'
        cpulimstr = os.getenv('LAB_CPU_LIMIT')
        cpulim = 1.0
        if cpulimstr:
            cpulim = float(cpulimstr)
        cpuguar = 0.02
        cpuguarstr = os.getenv('LAB_CPU_GUARANTEE')
        if cpuguarstr:
            cpuguar = float(cpuguarstr)
        spawner.mem_limit = memlim
        spawner.cpu_limit = cpulim
        spawner.mem_guarantee = memguar
        spawner.cpu_guarantee = cpuguar
        # Persistent shared user volume
        volname = "jld-fileserver-home"
        homefound = False
        for v in spawner.volumes:
            if v["name"] == volname:
                homefound = True
                break
        if not homefound:
            spawner.volumes.extend([
                {"name": volname,
                 "persistentVolumeClaim":
                 {"claimName": volname}}])
            spawner.volume_mounts.extend([
                {"mountPath": "/home",
                 "name": volname}])
        # We are running the Lab at the far end, not the old Notebook
        spawner.default_url = '/lab'
        spawner.singleuser_image_pull_policy = 'Always'
        # Let us set the images from the environment.
        # Get (possibly list of) image(s)
        imgspec = os.getenv("LAB_CONTAINER_NAMES")
        if not imgspec:
            imgspec = "lsstsqre/jld-lab:latest"
        imagelist = imgspec.split(',')
        if len(imagelist) < 2:
            spawner.singleuser_image_spec = imgspec
        else:
            spawner.singleuser_image_spec = imagelist[0]
            # Referenced from 10-options_form.py
            spawner.options_form = optform

        # Add extra configuration from auth_state
        if not self.enable_auth_state:
            return
        auth_state = yield user.get_auth_state()
        gh_user = auth_state.get("github_user")
        gh_token = auth_state.get("access_token")
        if gh_user:
            gh_id = gh_user.get("id")
        gh_org = yield self._get_user_organizations(gh_token)
        gh_email = gh_user.get("email")
        if not gh_email:
            gh_email = yield self._get_user_email(gh_token)
        if gh_email:
            spawner.environment['GITHUB_EMAIL'] = gh_email
        gh_name = gh_user.get("name")
        if not gh_name:
            gh_name = gh_user.get("login")
        if gh_id:
            spawner.environment['EXTERNAL_UID'] = str(gh_id)
        if gh_org:
            orglstr = ""
            for k in gh_org:
                if orglstr:
                    orglstr += ","
                orglstr += k + ":" + str(gh_org[k])
            spawner.environment['EXTERNAL_GROUPS'] = orglstr
        if gh_name:
            spawner.environment['GITHUB_NAME'] = gh_name
        if gh_token:
            spawner.environment['GITHUB_ACCESS_TOKEN'] = "[secret]"
            self.log.info("Spawned environment: %s", json.dumps(
                spawner.environment, sort_keys=True, indent=4))
            spawner.environment['GITHUB_ACCESS_TOKEN'] = gh_token

    @gen.coroutine
    def _get_user_organizations(self, access_token):
        """Get list of orgs user is a member of.  Requires 'read:org'
        token scope.
        """

        http_client = AsyncHTTPClient()
        headers = _api_headers(access_token)
        next_page = "https://%s/user/orgs" % (GITHUB_API)
        orgmap = {}
        while next_page:
            req = HTTPRequest(next_page, method="GET", headers=headers)
            try:
                resp = yield http_client.fetch(req)
            except HTTPError:
                return None
            resp_json = json.loads(resp.body.decode('utf8', 'replace'))
            next_page = next_page_from_links(resp)
            for entry in resp_json:
                # This could result in non-unique groups, if the first 32
                #  characters of the group names are the same.
                normalized_group = entry["login"][:32]
                orgmap[normalized_group] = entry["id"]
        return orgmap

    @gen.coroutine
    def _get_user_email(self, access_token):
        """Determine even private email, if the token has 'user:email'
        scope."""
        http_client = AsyncHTTPClient()
        headers = _api_headers(access_token)
        next_page = "https://%s/user/emails" % (GITHUB_API)
        while next_page:
            req = HTTPRequest(next_page, method="GET", headers=headers)
            resp = yield http_client.fetch(req)
            resp_json = json.loads(resp.body.decode('utf8', 'replace'))
            next_page = next_page_from_links(resp)
            for entry in resp_json:
                if "email" in entry:
                    if "primary" in entry and entry["primary"]:
                        return entry["email"]
        return None
