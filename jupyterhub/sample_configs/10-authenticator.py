'''Choose GitHub or CILogon authentication with the OAUTH_PROVIDER environment
variable, which must be one of "github", "cilogon" or "jwt", and defaults to
"github".
'''

import asyncio
import datetime
import json
import os
import oauthenticator
import random
from jupyterhub.handlers import LogoutHandler
from jupyterhub.utils import url_path_join
from jwtauthenticator.jwtauthenticator import JSONWebTokenAuthenticator
from jwtauthenticator.jwtauthenticator import JSONWebTokenLoginHandler
from oauthenticator.common import next_page_from_links
from tornado import gen, web
from tornado.httpclient import HTTPRequest, AsyncHTTPClient, HTTPError

# Get authenticator type; default to "github"
OAUTH_PROVIDER = os.environ.get('OAUTH_PROVIDER') or "github"

# Support github.com and github enterprise installations
GITHUB_HOST = os.environ.get('GITHUB_HOST') or 'github.com'
if GITHUB_HOST == 'github.com':
    GITHUB_API = 'api.github.com'
else:
    GITHUB_API = '%s/api/v3' % GITHUB_HOST

# Utility definition from GitHub OAuthenticator.


def _api_headers(access_token):
    return {"Accept": "application/json",
            "User-Agent": "JupyterHub",
            "Authorization": "token {}".format(access_token)
            }


# CILogon settings
CILOGON_HOST = os.environ.get('CILOGON_HOST') or 'cilogon.org'
STRICT_LDAP_GROUPS = os.environ.get('STRICT_LDAP_GROUPS')


# Enable the GitHub authenticator to spawn with additional information acquired
# with token with larger-than-default scope.
class LSSTGitHubAuth(oauthenticator.GitHubOAuthenticator):
    """
    This authenticator uses GitHub organization membership to make
    authentication and authorization decisions.
    """
    enable_auth_state = True

    _state = None

    groups = []

    login_handler = oauthenticator.GitHubLoginHandler

    @gen.coroutine
    def authenticate(self, handler, data=None):
        """Check for deny list membership too."""
        token = None
        userdict = yield super().authenticate(handler, data)
        try:
            token = userdict["auth_state"]["access_token"]
        except (KeyError, TypeError):
            self.log.warning("Could not extract access token.")
        if token:
            self.log.debug("Setting authenticator groups from token.")
            _ = yield self.set_groups_from_token(token)
        else:
            self.log.debug("No token found.")
        denylist = os.environ.get('GITHUB_ORGANIZATION_DENYLIST')
        if denylist:
            if not token:
                self.log.warning("User does not have access token.")
                userdict = None
            else:
                self.log.debug("Denylist `%s` found." % denylist)
                denylist = denylist.split(',')
                denied = yield self._check_denylist(userdict, denylist)
            if denied:
                self.log.warning("Rejecting user: denylisted")
                userdict = None
        return userdict

    @gen.coroutine
    def set_groups_from_token(self, token):
        self.log.debug("Acquiring list of user organizations.")
        gh_org = yield self._get_user_organizations(token)
        if not gh_org:
            self.log.warning("Could not get list of user organizations.")
        self.groups = gh_org
        self.log.debug("Set user organizations to '{}'.".format(gh_org))
        yield
        return

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


class LSSTCILogonAuth(oauthenticator.CILogonOAuthenticator):
    """
    This authenticator uses CILogon and the NCSA identity provider to make
    authentication and authorization decisions.
    """
    enable_auth_state = True
    _state = None
    login_handler = oauthenticator.CILogonLoginHandler
    allowed_groups = os.environ.get("CILOGON_GROUP_WHITELIST") or "lsst_users"
    forbidden_groups = os.environ.get("CILOGON_GROUP_DENYLIST")
    additional_username_claims = ["uid"]
    groups = []

    @gen.coroutine
    def authenticate(self, handler, data=None):
        """Rely on the superclass to do most of the work.
        """
        userdict = yield super().authenticate(handler, data)

        if userdict:
            membership = yield self._check_group_membership(userdict)
            if not membership:
                userdict = None
        if userdict and "cilogon_user" in userdict["auth_state"]:
            user_rec = userdict["auth_state"]["cilogon_user"]
            if "eppn" in user_rec:
                username, domain = user_rec["eppn"].split("@")
            if "uid" in user_rec:
                username = user_rec["uid"]
                domain = ""
            if domain and domain != self._default_domain:
                username = username + "." + domain
            userdict["name"] = username
        return userdict

    @gen.coroutine
    def _check_group_membership(self, userdict):
        if ("auth_state" not in userdict or not userdict["auth_state"]):
            self.log.warn("User doesn't have auth_state")
            return False
        ast = userdict["auth_state"]
        cu = ast["cilogon_user"]
        if "isMemberOf" in cu:
            has_member = yield self._check_member_of(cu["isMemberOf"])
            if not has_member:
                return False
        if ("token_response" not in ast or not ast["token_response"] or
            "id_token" not in ast["token_response"] or not
                ast["token_response"]["id_token"]):
            self.log.warn("User doesn't have ID token!")
            return False
        self.log.debug("Auth State: %s" % json.dumps(ast, sort_keys=True,
                                                     indent=4))
        return True

    @gen.coroutine
    def _set_groups(self, grouplist):
        grps = [x["name"] for x in grouplist]
        self.log.debug("Groups: %s" % str(grps))
        self.groups = grps

    @gen.coroutine
    def _check_member_of(self, grouplist):
        self.log.info("Using isMemberOf field.")
        allowed_groups = self.allowed_groups.split(",")
        forbidden_groups = self.forbidden_groups.split(",")
        self._set_groups(grouplist)
        user_groups = self.groups
        deny = list(set(forbidden_groups) & set(user_groups))
        if deny:
            self.log.warning("User in forbidden group: %s" % str(deny))
            return False
        self.log.debug("User not in forbidden groups: %s" %
                       str(forbidden_groups))
        intersection = list(set(allowed_groups) &
                            set(user_groups))
        if intersection:
            self.log.debug("User in groups: %s" % str(intersection))
            return True
        self.log.warning("User not in any groups %s" % str(allowed_groups))
        return False

    # We should refactor this out into a mixin class.
    @gen.coroutine
    def pre_spawn_start(self, user, spawner):
        """Add extra configuration from auth_state.
        """
        if not self.enable_auth_state:
            return
        auth_state = yield user.get_auth_state()
        if auth_state:
            save_token = auth_state["token_response"]
            auth_state["token_response"] = "[secret]"
            self.log.info("auth_state: %s", json.dumps(auth_state,
                                                       indent=4,
                                                       sort_keys=True))
            auth_state["token_response"] = save_token
            if "cilogon_user" in auth_state:
                user_rec = auth_state["cilogon_user"]
                # Get UID and GIDs from OAuth reply
                uid = user_rec.get("uidNumber")
                if uid:
                    uid = str(uid)
                else:
                    # Fake it
                    sub = user_rec.get("sub")
                    if sub:
                        uid = sub.split("/")[-1]  # Pretend last field is UID
                spawner.environment['EXTERNAL_UID'] = uid
                membership = user_rec.get("isMemberOf")
                if membership:
                    # We use a fake number if there is no matching 'id'
                    # Pick something outside of 16 bits, way under 32,
                    #  and high enough that we are unlikely to have
                    #  collisions.  Turn on STRICT_LDAP_GROUPS by
                    #  setting the environment variable if you want to
                    #  just skip those.
                    gidlist = []
                    grpbase = 3E7
                    grprange = 1E7
                    igrp = random.randint(grpbase, (grpbase + grprange))
                    for group in membership:
                        gname = group["name"]
                        if "id" in group:
                            gid = group["id"]
                        else:
                            # Skip if strict groups and no GID
                            if STRICT_LDAP_GROUPS:
                                continue
                            gid = igrp
                            igrp = igrp + 1
                        gidlist.append(gname + ":" + str(gid))
                    grplist = ",".join(gidlist)
                    spawner.environment['EXTERNAL_GROUPS'] = grplist
                    # Might be nice to have a mixin to also get GitHub
                    # information...


class LSSTJWTLoginHandler(JSONWebTokenLoginHandler):
    # Slightly cheesy, but we know we are in fact using the NCSA IDP at
    #  CILogon as the source of truth
    allowed_groups = os.environ.get("CILOGON_GROUP_WHITELIST") or "lsst_users"
    forbidden_groups = os.environ.get("CILOGON_GROUP_DENYLIST")

    @gen.coroutine
    def get(self):
        # This is taken from https://github.com/mogthesprog/jwtauthenticator
        #  but with our additional claim information checked and stuffed
        #  into auth_state, and allow/deny lists checked.
        claims, token = self._check_auth_header()
        username_claim_field = self.authenticator.username_claim_field
        username = self.retrieve_username(claims, username_claim_field)
        # Here is where we deviate from the vanilla JWT authenticator.
        # We simply store all the JWT claims in auth_state, although we also
        #  choose our field names to make the spawner reusable from the
        #  OAuthenticator implementation.
        auth_state = {"id": username,
                      "access_token": token,
                      "claims": claims}
        user = self.user_from_username(username)
        if not self.validate_user_from_claims_groups(claims):
            # We're either in a forbidden group, or not in any allowed group
            self.log.error("User did not validate from claims groups.")
            raise web.HTTPError(403)
        self.log.debug("Claims for user: {}".format(claims))
        self.log.debug("Membership: {}".format(claims["isMemberOf"]))
        gnames = [x["name"] for x in claims["isMemberOf"]]
        self.log.debug("Setting authenticator groups: {}.".format(gnames))
        self.authenticator.groups = gnames
        modified_auth_state = self._mogrify_auth_state(auth_state)
        yield user.save_auth_state(modified_auth_state)
        self.set_login_cookie(user)

        _url = url_path_join(self.hub.server.base_url, 'home')
        next_url = self.get_argument('next', default=False)
        if next_url:
            _url = next_url

        self.redirect(_url)

    async def refresh_user(self, user, handler=None):
        self.log.debug("Refreshing user data.")
        try:
            claims, token = self._check_auth_header()
        except web.HTTPError:
            # Force re-login
            return False
        username_claim_field = self.authenticator.username_claim_field
        username = self.retrieve_username(claims, username_claim_field)
        auth_state = {"id": username,
                      "access_token": token,
                      "claims": claims}
        modified_auth_state = self._mogrify_auth_state(auth_state)
        return modified_auth_state

    def _check_auth_header(self):
        # Either returns (valid) claims and token,
        #  or throws a web error of some type.
        self.log.debug("Checking authentication header.")
        header_name = self.authenticator.header_name
        param_name = self.authenticator.param_name
        header_is_authorization = self.authenticator.header_is_authorization
        auth_header_content = self.request.headers.get(header_name, "")
        auth_cookie_content = self.get_cookie("XSRF-TOKEN", "")
        signing_certificate = self.authenticator.signing_certificate
        secret = self.authenticator.secret
        audience = self.authenticator.expected_audience
        tokenParam = self.get_argument(param_name, default=False)
        if auth_header_content and tokenParam:
            self.log.error("Authentication: both an authentication header " +
                           "and tokenParam")
            raise web.HTTPError(400)
        elif auth_header_content:
            if header_is_authorization:
                # We should not see "token" as first word in the
                #  AUTHORIZATION header.  If we do it could mean someone
                #  coming in with a stale API token
                if auth_header_content.split()[0].lower() != "bearer":
                    self.log.error("Authorization header is not 'bearer'.")
                    raise web.HTTPError(403)
                token = auth_header_content.split()[1]
            else:
                token = auth_header_content
        elif auth_cookie_content:
            token = auth_cookie_content
        elif tokenParam:
            token = tokenParam
        else:
            self.log.error("Could not determine authentication token.")
            raise web.HTTPError(401)

        claims = ""
        if secret:
            claims = self.verify_jwt_using_secret(token, secret, audience)
        elif signing_certificate:
            claims = self.verify_jwt_with_claims(token, signing_certificate,
                                                 audience)
        else:
            self.log.error("Could not verify JWT.")
            raise web.HTTPError(401)

        # Check expiration
        expiry = int(claims['exp'])
        now = int(datetime.datetime.utcnow().timestamp())
        if now > expiry:
            self.log.error("JWT has expired!")
            raise web.HTTPError(401)
        return claims, token

    def _mogrify_auth_state(self, auth_state):
        astate = dict(auth_state)
        self.log.debug("Pre-mogrification auth state: %r" % astate)
        #
        # Do things here.
        #
        self.log.debug("Post-mogrification auth state: %r" % astate)
        return astate

    def validate_user_from_claims_groups(self, claims):
        alist = self.allowed_groups.split(',')
        dlist = []
        if self.forbidden_groups is not None:
            dlist = self.forbidden_groups.split(',')
        membership = [x["name"] for x in claims["isMemberOf"]]
        intersection = list(set(dlist) & set(membership))
        if intersection:
            # User is in at least one forbidden group.
            return False
        intersection = list(set(alist) & set(membership))
        if not intersection:
            # User is not in at least one allowed group.
            return False
        return True


class LSSTJWTLogoutHandler(LogoutHandler):
    """Redirect to OAuth2 sign_in"""

    async def render_logout_page(self):
        logout_url = os.getenv("LOGOUT_URL") or "/oauth2/sign_in"
        self.redirect(logout_url, permanent=False)


class LSSTJWTAuth(JSONWebTokenAuthenticator):
    enable_auth_state = True
    header_name = "X-Portal-Authorization"
    groups = []

    def get_handlers(self, app):
        return [
            (r'/login', LSSTJWTLoginHandler),
            (r'/logout', LSSTJWTLogoutHandler)
        ]

    # We should refactor this out into a mixin class.
    @gen.coroutine
    def pre_spawn_start(self, user, spawner):
        """Add extra configuration from auth_state.
        """
        if not self.enable_auth_state:
            return
        auth_state = yield user.get_auth_state()
        if auth_state:
            token = auth_state.get("access_token")
            if token:
                spawner.environment["ACCESS_TOKEN"] = token
            claims = auth_state.get("claims")
            if claims:
                # Get UID and GIDs from OAuth reply
                uid = claims.get("uidNumber")
                if uid:
                    uid = str(uid)
                else:
                    # Fake it
                    sub = claims.get("sub")
                    if sub:
                        uid = sub.split("/")[-1]  # Pretend last field is UID
                spawner.environment['EXTERNAL_UID'] = uid
                email = claims.get("email")
                if email:
                    spawner.environment['GITHUB_EMAIL'] = email
                membership = claims.get("isMemberOf")
                if membership:
                    # We use a fake number if there is no matching 'id'
                    # Pick something outside of 16 bits, way under 32,
                    #  and high enough that we are unlikely to have
                    #  collisions.  Turn on STRICT_LDAP_GROUPS by
                    #  setting the environment variable if you want to
                    #  just skip those.
                    gidlist = []
                    grpbase = 3E7
                    grprange = 1E7
                    igrp = random.randint(grpbase, (grpbase + grprange))
                    for group in membership:
                        gname = group["name"]
                        if "id" in group:
                            gid = group["id"]
                        else:
                            # Skip if strict groups and no GID
                            if STRICT_LDAP_GROUPS:
                                continue
                            gid = igrp
                            igrp = igrp + 1
                        gidlist.append(gname + ":" + str(gid))
                    grplist = ",".join(gidlist)
                    spawner.environment['EXTERNAL_GROUPS'] = grplist
                    # Might be nice to have a mixin to also get GitHub
                    # information...


# Set scope for GitHub
c.LSSTGitHubAuth.scope = [u'public_repo', u'read:org', u'user:email']

# Set scope for CILogon
c.LSSTCILogonAuth.scope = ['openid', 'org.cilogon.userinfo']

# Default to GitHub
c.JupyterHub.authenticator_class = LSSTGitHubAuth
if OAUTH_PROVIDER == "cilogon":
    c.JupyterHub.authenticator_class = LSSTCILogonAuth
if OAUTH_PROVIDER == "jwt":
    c.JupyterHub.authenticator_class = LSSTJWTAuth
