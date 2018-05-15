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


# Enable the authenticator to spawn with additional information acquired
# with token with larger-than-default scope.
class LSSTAuth(oauthenticator.GitHubOAuthenticator):
    """Authenticator to use our custom environment settings.
    """
    enable_auth_state = True

    _state = None

    login_handler = oauthenticator.GitHubLoginHandler

    @gen.coroutine
    def authenticate(self, handler, data=None):
        """Check for deny list membership too."""
        userdict = yield super().authenticate(handler, data)
        denylist = os.environ.get('GITHUB_ORGANIZATION_DENYLIST')
        if denylist:
            self.log.debug("Denylist `%s` found." % denylist)
            denylist = denylist.split(',')
            denied = yield self._check_denylist(userdict, denylist)
            if denied:
                self.log.warning("Rejecting user: denylisted")
                userdict = None
        return userdict

    @gen.coroutine
    def _check_denylist(self, userdict, denylist):
        if ("auth_state" not in userdict or not userdict["auth_state"]):
            self.log.warning("User doesn't have auth_state: rejecting.")
            return True
        ast = userdict["auth_state"]
        if ("access_token" not in ast or not ast["access_token"]):
            self.log.warning("User doesn't have access token: rejecting.")
            return True
        tok = ast["access_token"]
        gh_org = yield self._get_user_organizations(tok)
        if not gh_org:
            self.log.warning("Could not get list of GH user orgs: rejecting.")
            return True
        deny = list(set(gh_org) & set(denylist))
        if deny:
            self.log.warning("User in denylist %s: rejecting." % str(deny))
            return True
        self.log.debug("User not in denylist %s" % str(denylist))
        return False

    @gen.coroutine
    def pre_spawn_start(self, user, spawner):
        """Add extra configuration from auth_state.
        """
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
        gh_login = gh_user.get("login")
        gh_name = gh_user.get("name") or gh_login
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
        if gh_login:
            spawner.environment['GITHUB_LOGIN'] = gh_login
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

c.JupyterHub.authenticator_class = LSSTAuth
c.LSSTAuth.scope = [u'public_repo', u'read:org', u'user:email']
