# This is the JupyterHub configuration file LSST DM-SQuaRE uses.

# It spawns JupyterLab containers and does its authentication using
#  GitHub organization membership (and on the Lab pods, it does some magic
#  to set the UID equal to the GitHub ID and GIDs that match orgs).

# If it doesn't work for you, replace it in your Kubernetes config.
# It's mapped in as a configmap.  Look at the deployment file:
# jld-hub-config/jld-hub-cfg.py ->
#  /opt/lsst/software/jupyterhub/config/jupyterhub_config.py

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


class LSSTAuth(oauthenticator.GitHubOAuthenticator):
    """Authenticator to use our custom environment settings.
    """
    enable_auth_state = True

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
        spawner.volumes.extend([
            {"name": "jld-fileserver-home",
             "persistentVolumeClaim": {"claimName": "jld-fileserver-home"}}])
        spawner.volume_mounts.extend([
            {"mountPath": "/home",
             "name": "jld-fileserver-home"}])
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
        gh_id = auth_state.get("uid")
        gh_token = auth_state.get("access_token")
        gh_org = auth_state.get("organization_map")
        gh_email = auth_state.get("email")
        gh_name = auth_state.get("name")
        if not gh_name:
            gh_name = auth_state.get("username")
        if gh_id:
            spawner.environment['GITHUB_ID'] = str(gh_id)
        if gh_token:
            spawner.environment['GITHUB_ACCESS_TOKEN'] = gh_token
        if gh_org:
            orglstr = ""
            for k in gh_org:
                if orglstr:
                    orglstr += ","
                orglstr += k + ":" + str(gh_org[k])
            spawner.environment['GITHUB_ORGANIZATIONS'] = orglstr
        if gh_email:
            spawner.environment['GITHUB_EMAIL'] = gh_email
        if gh_name:
            spawner.environment['GITHUB_NAME'] = gh_name


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

        # Add a hack to ensure that no service accounts are mounted in spawned pods
        # This makes sure that we don"t accidentally give access to the whole
        # kubernetes API to the users in the spawned pods.
        # See
        # https://github.com/kubernetes/kubernetes/issues/16779#issuecomment-157460294
        hack_volume = V1Volume()
        hack_volume.name = "no-api-access-please"
        hack_volume.empty_dir = {}

        hack_volume_mount = V1VolumeMount()
        hack_volume_mount.name = "no-api-access-please"
        hack_volume_mount.mount_path = "/var/run/secrets/kubernetes.io/serviceaccount"
        hack_volume_mount.read_only = True

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
        self.singleuser_image_spec = image_spec
        self.log.info("Replacing image spec from options form: %s" %
                      image_spec)
        s_idx = image_spec.find('/')
        c_idx = image_spec.find(':')
        if s_idx != -1:
            image_name = image_spec[(s_idx + 1):]
            if c_idx > 0:
                image_name = image_spec[(s_idx + 1):c_idx]
        pn_template = image_name + "-{username}-{userid}"
        auth_state = yield self.user.get_auth_state()
        if auth_state and "uid" in auth_state:
            if auth_state["uid"] != self.user.id:
                self.log.info("Updating userid from %d to %d" %
                              (self.user.id, auth_state["uid"]))
                self.user.id = auth_state["uid"]
        self.log.info("Image template: %s" % pn_template)
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
            env=pod_env,
            volumes=self._expand_all(self.volumes) + [hack_volume],
            volume_mounts=self._expand_all(
                self.volume_mounts) + [hack_volume_mount],
            working_dir=self.singleuser_working_dir,
            labels=labels,
            cpu_limit=self.cpu_limit,
            cpu_guarantee=self.cpu_guarantee,
            mem_limit=self.mem_limit,
            mem_guarantee=self.mem_guarantee,
            lifecycle_hooks=self.singleuser_lifecycle_hooks,
            init_containers=self.singleuser_init_containers,
        )

    def options_from_form(self, formdata=None):
        options = {}
        if formdata and 'kernel_image' in formdata and formdata['kernel_image']:
            options['kernel_image'] = formdata['kernel_image'][0]
        return options

c.JupyterHub.authenticator_class = LSSTAuth
c.JupyterHub.spawner_class = LSSTSpawner

# Set up auth environment
c.LSSTAuth.oauth_callback_url = os.environ['OAUTH_CALLBACK_URL']
c.LSSTAuth.client_id = os.environ['GITHUB_CLIENT_ID']
c.LSSTAuth.client_secret = os.environ['GITHUB_CLIENT_SECRET']
c.LSSTAuth.github_organization_whitelist = set(
    (os.environ['GITHUB_ORGANIZATION_WHITELIST'].split(",")))

# Set options form
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
