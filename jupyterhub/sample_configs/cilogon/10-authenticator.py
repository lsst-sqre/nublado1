"""
This authenticator uses CILogon and the NCSA identity provider to make
authentication and authorization decisions.
"""
import json
import os
import oauthenticator
import random
from tornado import gen

CILOGON_HOST = os.environ.get('CILOGON_HOST') or 'cilogon.org'
STRICT_LDAP_GROUPS = os.environ.get('STRICT_LDAP_GROUPS')


class LSSTAuth(oauthenticator.CILogonOAuthenticator):
    """Authenticator to use our custom environment settings.
    """
    enable_auth_state = True
    _state = None
    _default_domain = "ncsa.illinois.edu"
    login_handler = oauthenticator.CILogonLoginHandler
    allowed_groups = os.environ.get("CILOGON_GROUP_WHITELIST") or "lsst_users"
    forbidden_groups = os.environ.get("CILOGON_GROUP_DENYLIST")

    @gen.coroutine
    def authenticate(self, handler, data=None):
        """Change username to something more sane. The 'eppn' field will have
        a username and a domain.  If the domain matches our default domain,
        just use the username; otherwise, use username prepended with a dot
        to the domain.
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
            if domain != self._default_domain:
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
    def _return_groups(self, grouplist):
        grps = [x["name"] for x in grouplist]
        self.log.debug("Groups: %s" % str(grps))
        return grps

    @gen.coroutine
    def _check_member_of(self, grouplist):
        self.log.info("Using isMemberOf field.")
        allowed_groups = self.allowed_groups.split(",")
        forbidden_groups = self.forbidden_groups.split(",")
        user_groups = yield self._return_groups(grouplist)
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
                    user_groups = yield self._return_groups(membership)
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


c.JupyterHub.authenticator_class = LSSTAuth
# Set scope, skin, and provider
c.LSSTAuth.scope = ['openid', 'org.cilogon.userinfo']
c.LSSTAuth.skin = "LSST"
c.LSSTAuth.idp = "https://idp.ncsa.illinois.edu/idp/shibboleth"
