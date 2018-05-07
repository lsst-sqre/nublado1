"""The spawner is the KubeSpawner, modified to use the options form data.
"""
import datetime
import escapism
import json
import kubespawner
import os
from urllib.error import HTTPError
from kubespawner.objects import make_pod
from tornado import gen
# https://github.com/lsst-sqre/jupyterutils
from jupyterutils import ScanRepo

# Spawn the pod with custom settings retrieved via token additional scope.


class LSSTSpawner(kubespawner.KubeSpawner):
    """Spawner to use our custom environment settings as reflected through
    auth_state."""

    def _options_form_default(self):
        # Make options form by scanning container repository
        title = os.getenv("LAB_SELECTOR_TITLE") or "Container Image Selector"
        owner = os.getenv("LAB_REPO_OWNER") or "lsstsqre"
        repo = os.getenv("LAB_REPO_NAME") or "jld-lab"
        host = os.getenv("LAB_REPO_HOST") or "hub.docker.com"
        scanner = ScanRepo(host=host,
                           owner=owner,
                           name=repo,
                           json=True,
                           )
        try:
            scanner.scan()
        except (ValueError, HTTPError) as e:
            self.log.warning("Could not get data from %s: %s/%s [%s]" %
                             (host, owner, repo, str(e)))
            return ""
        lnames, ldescs = scanner.extract_image_info()
        if not lnames or len(lnames) < 2:
            return ""
        optform = "<label for=\"%s\">%s</label><br />\n" % (title, title)
        now = datetime.datetime.now()
        nowstr = now.ctime()
        if not now.tzinfo:
            # If we don't have tzinfo, assume it's in UTC"
            nowstr += " UTC"
        optform = "<table>\n        <tr><td>"
        optform += "<b>Image</b><br /></td><td><b>Size</b><br /></td></tr>\n"
        optform += "        <tr><td>\n"
        checked = False
        for idx, img in enumerate(lnames):
            optform += "          "
            optform += "<input type=\"radio\" name=\"kernel_image\""
            optform += " value=\"%s\"" % img
            if not checked:
                checked = True
                optform += " checked=\"checked\""
            optform += ">%s<br />\n" % ldescs[idx]

        optform += "              "
        optform += "<input type=\"text\" name=\"image_tag\""
        optform += " value=\"or supply Image Tag\"><br />\n"
        optform += "          </td>\n          <td valign=\"top\">\n"
        checked = False
        for size in ["tiny", "small", "medium", "large"]:
            optform += "            "
            optform += "<input type=\"radio\" name=\"size\""
            if not checked:
                checked = True
                optform += " checked=\"checked\""
            optform += " value=\"%s\">%s<br />\n" % (size, size.title())
        optform += "          </td></tr>\n      </table>\n"
        optform += "<hr />\n"
        optform += "Menu updated at %s<br />\n" % nowstr
        return optform

    @property
    def options_form(self):
        return self._options_form_default()

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
            singleuser_fs_gid = yield \
                gen.maybe_future(self.singleuser_fs_gid(self))
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
        image_spec = (self.singleuser_image_spec or os.getenv("LAB_IMAGE")
                      or "lsstsqre/jld-lab:latest")
        image_name = image_spec
        image_size = None
        # First pulls can be really slow for the LSST stack containers,
        #  so let's give it a big timeout
        self.http_timeout = 60 * 15
        self.start_timeout = 60 * 15
        # The spawned containers need to be able to talk to the hub through
        #  the proxy!
        self.hub_connect_port = int(os.environ['JLD_HUB_SERVICE_PORT'])
        self.hub_connect_ip = os.environ['JLD_HUB_SERVICE_HOST']
        # We are running the Lab at the far end, not the old Notebook
        self.default_url = '/lab'
        self.singleuser_image_pull_policy = 'Always'
        if self.user_options:
            if self.user_options.get('image_tag'):
                colon = image_spec.find(':')
                if colon > -1:
                    im_n = image_name[:colon]
                    image_spec = im_n + ":" + \
                        self.user_options.get('image_tag')
                    image_name = image_spec
            elif self.user_options.get('kernel_image'):
                image_spec = self.user_options.get('kernel_image')
                image_name = image_spec
                self.log.info("Replacing image spec from options form: %s" %
                              image_spec)
            size = self.user_options.get('size')
            tiny_cpu = os.environ.get('TINY_MAX_CPU') or 0.5
            if type(tiny_cpu) is str:
                tiny_cpu = float(tiny_cpu)
            mem_per_cpu = os.environ.get('MB_PER_CPU') or 2048
            if type(mem_per_cpu) is str:
                mem_per_cpu = int(mem_per_cpu)
            szd = {}
            cpu = tiny_cpu
            for i in ["tiny", "small", "medium", "large"]:
                szd[i] = {"cpu": cpu,
                          "mem": mem_per_cpu * cpu}
                cpu = cpu * 2
            image_size = szd.get(size)
        mem_limit = os.getenv('LAB_MEM_LIMIT') or '2048M'
        cpu_limit = os.getenv('LAB_CPU_LIMIT') or 1.0
        if image_size:
            mem_limit = str(int(image_size["mem"])) + "M"
            cpu_limit = float(image_size["cpu"])
        if type(cpu_limit) is str:
            cpu_limit = float(cpu_limit)
        self.mem_limit = mem_limit
        self.cpu_limit = cpu_limit
        mem_guar = os.getenv('LAB_MEM_GUARANTEE') or '64K'
        cpu_guar = os.getenv('LAB_CPU_GUARANTEE') or 0.02
        if type(cpu_guar) is str:
            cpu_guar = float(cpu_guar)
        # Tiny gets the "basically nothing" above (or the explicit
        #  guarantee).  All others get 1/LAB_SIZE_RANGE times their
        #  maximum, with a default of 1/4.
        size_range = os.getenv('LAB_SIZE_RANGE') or 4.0
        if type(size_range) is str:
            size_range = float(size_range)
        if image_size and self.user_options.get('size') != 'tiny':
            mem_guar = int(image_size["mem"] / size_range)
            cpu_guar = float(image_size["cpu"] / size_range)
        self.mem_guarantee = mem_guar
        self.cpu_guarantee = cpu_guar
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
        auth_state = yield self.user.get_auth_state()
        if auth_state and "id" in auth_state:
            if auth_state["id"] != self.user.id:
                self.log.info("Updating userid from %d to %d" %
                              (self.user.id, auth_state["id"]))
        pod_name = self._expand_user_properties(pn_template)
        self.pod_name = pod_name
        self.log.info("Replacing pod name from options form: %s" %
                      pod_name)
        pod_env = self.get_env()
        idle_timeout = int(os.getenv('LAB_IDLE_TIMEOUT') or 43200)
        if idle_timeout > 0 and 'JUPYTERLAB_IDLE_TIMEOUT' not in pod_env:
            pod_env['JUPYTERLAB_IDLE_TIMEOUT'] = str(idle_timeout)
        oauth_callback = os.getenv('OAUTH_CALLBACK_URL')
        endstr = "/hub/oauth_callback"
        if oauth_callback and oauth_callback.endswith(endstr):
            pod_env['EXTERNAL_URL'] = oauth_callback[:-len(endstr)]
        if os.getenv('DEBUG'):
            pod_env['DEBUG'] = os.getenv('DEBUG')
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
        for v in self.volumes:
            if v["name"] == volname:
                homefound = True
                break
        if not homefound:
            self.volumes.extend([
                {"name": volname,
                 "persistentVolumeClaim":
                 {"claimName": volname}}])
            self.volume_mounts.extend([
                {"mountPath": "/home",
                 "name": volname,
                 "accessModes": ["ReadWriteMany"]}])
        for vol in ["project", "scratch"]:
            volname = "jld-fileserver-" + vol
            self.volumes.extend([
                {"name": volname,
                 "persistentVolumeClaim": {"claimName": volname}}])
            self.volume_mounts.extend([
                {"mountPath": "/" + vol,
                 "name": volname,
                 "accessModes": ["ReadWriteMany"]}])
        for vol in ["datasets", "software"]:
            volname = "jld-fileserver-" + vol
            self.volumes.extend([
                {"name": volname,
                 "persistentVolumeClaim": {"claimName": volname}}])
            self.volume_mounts.extend([
                {"mountPath": "/" + vol,
                 "name": volname,
                 "accessModes": ["ReadOnlyMany"]}])
        self.log.debug("Volumes: %s" % json.dumps(self.volumes,
                                                  indent=4,
                                                  sort_keys=True))
        self.log.debug("Volume mounts: %s" % json.dumps(self.volume_mounts,
                                                        indent=4,
                                                        sort_keys=True))

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
        if (formdata and 'kernel_image' in formdata and
                formdata['kernel_image']):
            options['kernel_image'] = formdata['kernel_image'][0]
        return options


c.JupyterHub.spawner_class = LSSTSpawner
