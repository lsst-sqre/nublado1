"""
This authenticator uses CILogon and the NCSA identity provider to make
authentication and authorization decisions.
"""
import json
import os
import oauthenticator
from tornado import gen, web
from tornado.httpclient import HTTPRequest, AsyncHTTPClient
from tornado.httputil import url_concat

CILOGON_HOST = os.environ.get('CILOGON_HOST') or 'cilogon.org'


class LSSTAuth(oauthenticator.CILogonOAuthenticator):
    """Authenticator to use our custom environment settings.
    """
    enable_auth_state = True
    _state = None
    _default_domain = "ncsa.illinois.edu"
    login_handler = oauthenticator.CILogonLoginHandler
    allowed_groups = os.environ.get("CILOGON_GROUP_WHITELIST") or "lsst_users"

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
        url = "https://%s/oauth2/util" % CILOGON_HOST
        token = ast["token_response"]["id_token"]
        params = {
            "action": "check_claim",
            "claim_name": "isMemberOf",
            "token": token
        }
        allowed_groups = self.allowed_groups.split(",")
        http_client = AsyncHTTPClient()
        uname = userdict["name"]
        for group in allowed_groups:
            params.update({"claim_value": "cn=%s" % group})
            param_url = url_concat(url, params)
            req = HTTPRequest(param_url, method="GET")
            resp = yield http_client.fetch(req)
            text = resp.body.decode('utf8', 'replace').rstrip()
            if text == u"yes":
                self.log.info("User %s is in group %s" % (uname, group))
                return True
            elif text == u"no":
                self.log.info("User %s is not in group %s" % (uname, group))
            else:
                self.log.info("Response %s for user %s / group %s" %
                              (text, uname, group))
        self.log.warn("User %s not in any group in %r" %
                      (uname, allowed_groups))
        return False

    @gen.coroutine
    def _return_groups(self, grouplist):
        grps = []
        for ldapfield in grouplist:
            fldlist = ldapfield.split(",")
            rec = {}
            for fld in fldlist:
                k, v = fld.split("=")
                rec[k] = v  # This flattens dc but we don't care
            if "ou" not in rec or rec["ou"] != "Groups":
                continue  # Not the droid we're looking_for
            grps.append(rec["cn"])
        return grps

    @gen.coroutine
    def _check_member_of(self, grouplist):
        self.log.info("Using undocumented isMemberOf field.")
        allowed_groups = self.allowed_groups.split(",")
        user_groups = yield self._return_groups(grouplist)
        intersection = list(set(allowed_groups) &
                            set(user_groups))
        if intersection:
            return True
        return False

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
        # The standard set of LSST volumes is mountpoints at...
        #  /home
        #  /project
        #  /scratch
        #  /datasets
        #  /software
        # Where software and datasets are read/only and the others are
        #  read/write
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
        for vol in ["project", "scratch"]:
            volname = "jld-fileserver-" + vol
            spawner.volumes.extend([
                {"name": volname,
                 "persistentVolumeClaim": {"claimName": volname}}])
            spawner.volume_mounts.extend([
                {"mountPath": "/" + vol,
                 "name": volname,
                 "accessModes": ["ReadWriteMany"]}])
        for vol in ["datasets", "software"]:
            volname = "jld-fileserver-" + vol
            spawner.volumes.extend([
                {"name": volname,
                 "persistentVolumeClaim": {"claimName": volname}}])
            spawner.volume_mounts.extend([
                {"mountPath": "/" + vol,
                 "name": volname,
                 "accessModes": ["ReadOnlyMany"]}])
        self.log.debug("Volumes: %s" % json.dumps(spawner.volumes,
                                                  indent=4,
                                                  sort_keys=True))
        self.log.debug("Volume mounts: %s" % json.dumps(spawner.volume_mounts,
                                                        indent=4,
                                                        sort_keys=True))
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

        # Add extra configuration from auth_state
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
                sub = user_rec.get("sub")
                if sub:
                    uid = sub.split("/")[-1]  # We pretend last field is UID
                    spawner.environment['EXTERNAL_UID'] = uid
                    # We want UID/GIDs from OAuth2
                membership = user_rec.get("isMemberOf")
                if membership:
                    user_groups = yield self._return_groups(membership)
                    gidlist = []
                    # This is faked until we get GIDs from OAuth2
                    igrp = 5000
                    for grp in user_groups:
                        gidlist.append(grp + ":" + str(igrp))
                        igrp = igrp + 1
                    grplist = ",".join(gidlist)
                    spawner.environment['EXTERNAL_GROUPS'] = grplist
                    # Might be nice to have a mixin to also get GitHub
                    # information...


c.JupyterHub.authenticator_class = LSSTAuth
# Set scope, skin, and provider
c.LSSTAuth.scope = ['openid', 'email', 'profile', 'org.cilogon.userinfo']
c.LSSTAuth.skin = "LSST"
c.LSSTAuth.idp = "https://idp.ncsa.illinois.edu/idp/shibboleth"
