# This is the JupyterHub configuration file LSST DM-SQuaRE uses for NCSA
#  CILogon logins.

# It spawns JupyterLab containers and does its authentication using
#  CILogon with the NCSA identity provider.

# If it doesn't work for you, replace it in your Kubernetes config.
# It's mapped in as a configmap.  Look at the deployment file:
# jld-hub-config/jld-hub-cfg.py ->
#  /opt/lsst/software/jupyterhub/config/jupyterhub_config.py

import json
import os
import escapism
import kubespawner
import oauthenticator
from kubernetes.client.models.v1_volume import V1Volume
from kubernetes.client.models.v1_volume_mount import V1VolumeMount
from kubespawner.objects import make_pod
from tornado import gen


# Make options form
title = os.getenv("LAB_SELECTOR_TITLE")
if not title:
    title = "Container Image Selector"
imgspec = os.getenv("LAB_CONTAINER_NAMES")
if not imgspec:
    imgspec = "lsstsqre/jld-lab:latest"
imagelist = imgspec.split(',')
idescstr = os.getenv("LAB_CONTAINER_DESCS")
if not idescstr:
    idesc = imagelist
else:
    idesc = idescstr.split(',')
optform = "<label for=\"%s\">%s</label></br>\n" % (title, title)
for idx, img in enumerate(imagelist):
    optform += "      "
    optform += "<input type=\"radio\" name=\"kernel_image\""
    imgdesc = img
    try:
        imgdesc = idesc[idx]
    except IndexError:
        imgdesc = img
    if not imgdesc:
        imgdesc = img
    optform += " value=\"%s\">%s<br>\n" % (img, imgdesc)
# Options form built.

# Request additional scope on GitHub token to auto-provision magic in the
# user container.


class LSSTLoginHandler(oauthenticator.CILogonLoginHandler):
    """Request additional scope on CILogon token.

       Set skin to LSST.

       Use NCSA as identity provider.
    """
    scope = ['openid', 'email', 'profile', 'org.cilogon.userinfo']
    skin = "LSST"
    idp = "https://idp.ncsa.illinois.edu/idp/shibboleth"


# Enable the authenticator to spawn with additional information acquired
# with token with larger-than-default scope.
class LSSTAuth(oauthenticator.CILogonOAuthenticator):
    """Authenticator to use our custom environment settings.
    """
    enable_auth_state = True
    _state = None
    _default_domain = "ncsa.illinois.edu"
    login_handler = LSSTLoginHandler

    @gen.coroutine
    def authenticate(self, handler, data=None):
        """Change username to something more sane. The 'eppn' field will have
        a username and a domain.  If the domain matches our default domain,
        just use the username; otherwise, use username prepended with a dot
        to the domain.
        """
        userdict = yield super().authenticate(handler, data)
        if "auth_state" in userdict:
            if "cilogon_user" in userdict["auth_state"]:
                user_rec = userdict["auth_state"]["cilogon_user"]
                if "eppn" in user_rec:
                    username, domain = user_rec["eppn"].split("@")
                    if domain != self._default_domain:
                        username = username + "." + domain
                userdict["name"] = username
        return userdict

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
            spawner.options_form = optform

        # Add extra configuration from auth_state
        if not self.enable_auth_state:
            return
        auth_state = yield user.get_auth_state()
        if auth_state:
            save_token = auth_state["access_token"]
            auth_state["access_token"] = "[secret]"
            self.log.info("auth_state: %s", json.dumps(auth_state,
                                                       indent=4,
                                                       sort_keys=True))
            auth_state["access_token"] = save_token
            if "cilogon_user" in auth_state:
                user_rec = auth_state["cilogon_user"]
                sub = user_rec.get("sub")
                if sub:
                    uid = sub.split("/")[-1]  # Last field is UID
                    spawner.environment['EXTERNAL_UID'] = uid
            # Might be nice to have a mixin to also get GitHub information...


# Spawn the pod with custom settings retrieved via token additional scope.
class LSSTSpawner(kubespawner.KubeSpawner):
    """Spawner to use our custom environment settings as reflected through
    auth_state."""

    @gen.coroutine
    def get_pod_manifest(self):
        """
        Make a pod manifest that will spawn current user's notebook pod.
        """
        if callable(self.singleuser_uid):
            singleuser_uid = yield gen.maybe_future(self.singleuser_uid(self))
        else:
            singleuser_uid = self.singleuser_uid

        if callable(self.singleuser_fs_gid):
            singleuser_fs_gid = yield gen.maybe_future(self.singleuser_fs_gid(self))
        else:
            singleuser_fs_gid = self.singleuser_fs_gid

        if self.cmd:
            real_cmd = self.cmd + self.get_args()
        else:
            real_cmd = None
        # Default set of labels, picked up from
        # https://github.com/kubernetes/helm/blob/master/docs/chart_best_practices/labels.md
        labels = {
            'heritage': 'jupyterhub',
            'component': 'singleuser-server',
            'app': 'jupyterhub',
            'hub.jupyter.org/username': escapism.escape(self.user.name)
        }

        labels.update(self._expand_all(self.singleuser_extra_labels))

        pod_name = self.pod_name
        image_spec = self.singleuser_image_spec
        image_name = image_spec
        if self.user_options:
            if self.user_options.get('kernel_image'):
                image_spec = self.user_options.get('kernel_image')
                image_name = image_spec
                self.log.info("Replacing image spec from options form: %s" %
                              image_spec)
        self.singleuser_image_spec = image_spec
        s_idx = image_spec.find('/')
        c_idx = image_spec.find(':')
        tag = "latest"
        if s_idx != -1:
            image_name = image_spec[(s_idx + 1):]
            if c_idx > 0:
                image_name = image_spec[(s_idx + 1):c_idx]
                tag = image_spec[(c_idx + 1):]
        pn_template = image_name + "-{username}-" + tag
        pod_name = self._expand_user_properties(pn_template)
        self.pod_name = pod_name
        self.log.info("Replacing pod name from options form: %s" %
                      pod_name)
        pod_env = self.get_env()
        return make_pod(
            name=self.pod_name,
            image_spec=self.singleuser_image_spec,
            image_pull_policy=self.singleuser_image_pull_policy,
            image_pull_secret=self.singleuser_image_pull_secrets,
            port=self.port,
            cmd=real_cmd,
            node_selector=self.singleuser_node_selector,
            run_as_uid=singleuser_uid,
            fs_gid=singleuser_fs_gid,
            run_privileged=self.singleuser_privileged,
            env=pod_env,
            volumes=self._expand_all(self.volumes),
            volume_mounts=self._expand_all(self.volume_mounts),
            working_dir=self.singleuser_working_dir,
            labels=labels,
            cpu_limit=self.cpu_limit,
            cpu_guarantee=self.cpu_guarantee,
            mem_limit=self.mem_limit,
            mem_guarantee=self.mem_guarantee,
            lifecycle_hooks=self.singleuser_lifecycle_hooks,
            init_containers=self.singleuser_init_containers,
            service_account=None
        )

    def options_from_form(self, formdata=None):
        options = {}
        if formdata and 'kernel_image' in formdata and \
           formdata['kernel_image']:
            options['kernel_image'] = formdata['kernel_image'][0]
        return options

c.JupyterHub.authenticator_class = LSSTAuth
c.JupyterHub.spawner_class = LSSTSpawner

# Set up auth environment
c.LSSTAuth.oauth_callback_url = os.environ['OAUTH_CALLBACK_URL']
c.LSSTAuth.client_id = os.environ['CILOGON_CLIENT_ID']
c.LSSTAuth.client_secret = os.environ['CILOGON_CLIENT_SECRET']

# Set options form
if len(imagelist) > 1:
    c.LSSTSpawner.options_form = optform


# Listen to all interfaces
c.JupyterHub.ip = '0.0.0.0'
# Don't try to cleanup servers on exit - since in general for k8s, we want
# the hub to be able to restart without losing user containers
c.JupyterHub.cleanup_servers = False
# Set Hub IP explicitly
c.JupyterHub.hub_ip = os.environ['HUB_BIND_IP']
# Set Session DB URL if we have one
db_url = os.getenv('SESSION_DB_URL')
if db_url:
    c.JupyterHub.db_url = db_url
