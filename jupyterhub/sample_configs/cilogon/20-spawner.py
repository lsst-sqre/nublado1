"""The spawner is the KubeSpawner, modified to use the options form data.
"""
import datetime
import json
# import kubespawner
from kubespawner.objects import make_pod
import namespacedkubespawner
import os
from urllib.error import HTTPError
from tornado import gen
# https://github.com/lsst-sqre/jupyterhubutils, used to be jupyterutils
try:
    from jupyterhubutils import ScanRepo
except ImportError:
    from jupyterutils import ScanRepo
# Spawn the pod with custom settings retrieved via token additional scope.


class LSSTSpawner(namespacedkubespawner.NamespacedKubeSpawner):
    # class LSSTSpawner(kubespawner.KubeSpawner):
    """Spawner to use our custom environment settings as reflected through
    auth_state."""

    _sizemap = {}
    # In our LSST setup, there is a "provisionator" user, uid/gid 769,
    #  that is who we should start as.
    uid = 769
    gid = 769
    # The fields need to be defined; we don't use them.
    fs_gid = None
    supplemental_gids = []
    extra_labels = []
    extra_annotations = []
    image_pull_secrets = None
    privileged = False
    working_dir = None
    lifecycle_hooks = {}  # This one will be useful someday.
    init_containers = []
    service_account = None
    extra_container_config = None
    extra_pod_config = None
    extra_containers = []
    service_account = None
    if os.getenv("ALLOW_DASK_SPAWN"):
        service_account = "jld-dask"
    # Change some defaults.
    delete_namespace_on_stop = True
    duplicate_nfs_pvs_to_namespace = True
    # To add quota support:
    #  set enable_namespace_quotas = True
    # and then add a method:
    #  self.get_resource_quota_spec()
    #   which should return a kubernetes.client.V1ResourceQuotaSpec

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
        try:
            all_tags = scanner.get_all_tags()
        except AttributeError:
            all_tags = []
        optform = "<label for=\"%s\">%s</label><br />\n" % (title, title)
        now = datetime.datetime.now()
        nowstr = now.ctime()
        if not now.tzinfo:
            # If we don't have tzinfo, assume it's in UTC"
            nowstr += " UTC"
        optform = "<style>\n"
        optform += "    td#clear_dotlocal {\n"
        optform += "        border: 1px solid black;\n"
        optform += "        padding: 2%;\n"
        optform += "    }\n"
        optform += "    td#images {\n"
        optform += "        padding-right: 5%;\n"
        optform += "    }\n"
        optform += "</style>\n"
        optform += "<table>\n        <tr>"
        optform += "<th>Image</th></th><th>Size<br /></th></tr>\n"
        optform += "        <tr><td rowspan=2 id=\"images\">\n"
        self._make_sizemap()
        checked = False
        saveimg = ""
        for idx, img in enumerate(lnames):
            optform += "          "
            optform += " <input type=\"radio\" name=\"kernel_image\""
            optform += " value=\"%s\"" % img
            if not checked:
                checked = True
                saveimg = img
                optform += " checked=\"checked\""
            optform += "> %s<br />\n" % ldescs[idx]
        optform += "          "
        optform += " <input type=\"radio\" name=\"kernel_image\""
        colon = saveimg.find(':')
        custtag = saveimg[:colon] + ":__custom"
        optform += " value=\"%s\"> or select image tag " % custtag
        optform += "          "
        optform += "<select name=\"image_tag\">\n"
        optform += "          "
        optform += "<option value=\"latest\"><br /></option>\n"
        for tag in all_tags:
            optform += "            "
            optform += "<option value=\"%s\">%s<br /></option>\n" % (tag, tag)
        optform += "          </select><br />\n"
        optform += "          </td>\n          <td valign=\"top\">\n"
        checked = False
        sizemap = self._sizemap
        sizes = list(sizemap.keys())
        si = os.environ.get('SIZE_INDEX') or '1'
        size_index = int(si)
        if size_index >= len(sizes):
            size_index = 1
        defaultsize = sizes[size_index]
        for size in sizemap:
            optform += "            "
            optform += " <input type=\"radio\" name=\"size\""
            if size == defaultsize:
                checked = True
                optform += " checked=\"checked\""
            optform += " value=\"%s\"> %s<br />\n" % (size,
                                                      sizemap[size]["desc"])
        optform += "          </td></tr>\n"
        optform += "          <tr><td id=\"clear_dotlocal\">"
        optform += "<input type=\"checkbox\" name=\"clear_dotlocal\""
        optform += " value=\"true\">"
        optform += " Clear <tt>.local</tt> directory (caution!)<br />"
        optform += "</td></tr>\n"
        optform += "      </table>\n"
        optform += "<hr />\n"
        optform += "Menu updated at %s<br />\n" % nowstr
        return optform

    def _make_sizemap(self):
        sizes = ["tiny", "small", "medium", "large"]
        tiny_cpu = os.environ.get('TINY_MAX_CPU') or 0.5
        if type(tiny_cpu) is str:
            tiny_cpu = float(tiny_cpu)
        mem_per_cpu = os.environ.get('MB_PER_CPU') or 2048
        if type(mem_per_cpu) is str:
            mem_per_cpu = int(mem_per_cpu)
        cpu = tiny_cpu
        sizemap = {}
        for sz in sizes:
            mem = mem_per_cpu * cpu
            sizemap[sz] = {"cpu": cpu,
                           "mem": mem}
            desc = sz.title() + " (%.2f CPU, %dM RAM)" % (cpu, mem)
            sizemap[sz]["desc"] = desc
            cpu = cpu * 2
        self._sizemap = sizemap

    @property
    def options_form(self):
        return self._options_form_default()

    @gen.coroutine
    def get_pod_manifest(self):
        """
        Make a pod manifest that will spawn current user's notebook pod.
        """

        if callable(self.uid):
            uid = yield gen.maybe_future(self.uid(self))
        else:
            uid = self.uid

        if callable(self.gid):
            gid = yield gen.maybe_future(self.gid(self))
        else:
            gid = self.gid

        if callable(self.fs_gid):
            fs_gid = yield gen.maybe_future(self.fs_gid(self))
        else:
            fs_gid = self.fs_gid

        if callable(self.supplemental_gids):
            supplemental_gids = yield gen.maybe_future(self.supplemental_gids(self))
        else:
            supplemental_gids = self.supplemental_gids

        if self.cmd:
            real_cmd = self.cmd + self.get_args()
        else:
            real_cmd = None

        labels = self._build_pod_labels(self._expand_all(self.extra_labels))
        annotations = self._build_common_annotations(
            self._expand_all(self.extra_annotations))

        # The above was from the superclass.
        # This part is our custom LSST stuff.

        if os.getenv("ALLOW_DASK_SPAWN"):
            self.service_account = 'jld-dask'

        pod_name = self.pod_name
        image_spec = (self.image_spec or
                      os.getenv("LAB_IMAGE") or
                      "lsstsqre/jld-lab:latest")
        image_name = image_spec
        size = None
        image_size = None
        # First pulls can be really slow for the LSST stack containers,
        #  so let's give it a big timeout
        self.http_timeout = 60 * 15
        self.start_timeout = 60 * 15
        # We are running the Lab at the far end, not the old Notebook
        self.default_url = '/lab'
        self.image_pull_policy = 'Always'
        clear_dotlocal = False
        if self.user_options:
            self.log.debug("user_options: %s" % json.dumps(self.user_options,
                                                           sort_keys=True,
                                                           indent=4))
            if self.user_options.get('kernel_image'):
                image_spec = self.user_options.get('kernel_image')
                colon = image_spec.find(':')
                if colon > -1:
                    imgname = image_spec[:colon]
                    tag = image_spec[(colon + 1):]
                    self.log.debug("Image name: %s ; tag: %s" % (imgname, tag))
                    if tag == "__custom":
                        cit = self.user_options.get('image_tag')
                        if cit:
                            image_spec = imgname + ":" + cit
                image_name = image_spec
                self.log.info("Replacing image spec from options form: %s" %
                              image_spec)
                size = self.user_options.get('size')
                if size:
                    image_size = self._sizemap[size]
                clear_dotlocal = self.user_options.get('clear_dotlocal')
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
        if image_size and size != 'tiny':
            mem_guar = int(image_size["mem"] / size_range)
            cpu_guar = float(image_size["cpu"] / size_range)
        self.mem_guarantee = mem_guar
        self.cpu_guarantee = cpu_guar
        self.image_spec = image_spec
        s_idx = image_spec.find('/')
        c_idx = image_spec.find(':')
        tag = "latest"
        if s_idx != -1:
            image_name = image_spec[(s_idx + 1):]
            if c_idx > 0:
                image_name = image_spec[(s_idx + 1):c_idx]
                tag = image_spec[(c_idx + 1):].replace('_', '')
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
        if os.getenv('RESTRICT_DASK_NODES'):
            pod_env['RESTRICT_DASK_NODES'] = "true"
        if os.getenv('LAB_NODEJS_MAX_MEM'):
            pod_env['NODE_OPTIONS'] = ("--max-old-space-size=" +
                                       os.getenv('LAB_NODEJS_MAX_MEM'))
        oauth_callback = os.getenv('OAUTH_CALLBACK_URL')
        endstr = "/hub/oauth_callback"
        if oauth_callback and oauth_callback.endswith(endstr):
            pod_env['EXTERNAL_URL'] = oauth_callback[:-len(endstr)]
        if os.getenv('DEBUG'):
            pod_env['DEBUG'] = os.getenv('DEBUG')
        if clear_dotlocal:
            pod_env['CLEAR_DOTLOCAL'] = "true"
        firefly_route = os.getenv('FIREFLY_ROUTE') or "/firefly/"
        pod_env['FIREFLY_ROUTE'] = firefly_route
        auto_repo_urls = os.getenv('AUTO_REPO_URLS')
        if auto_repo_urls:
            pod_env['AUTO_REPO_URLS'] = auto_repo_urls
        # The standard set of LSST volumes is mountpoints at...
        #  /home
        #  /project
        #  /scratch
        #  /datasets
        # Where datasets is read/only and the others are read/write

        already_vols = []
        if self.volumes:
            already_vols = [x["name"] for x in self.volumes]
        for vol in ["home", "project", "scratch"]:
            volname = "jld-fileserver-" + vol
            if volname in already_vols:
                continue
            self.volumes.extend([
                {"name": volname,
                 "persistentVolumeClaim": {"claimName": volname,
                                           "accessModes": "ReadWriteMany"}}])
            self.volume_mounts.extend([
                {"mountPath": "/" + vol,
                 "name": volname}])
        for vol in ["datasets"]:
            volname = "jld-fileserver-" + vol
            if volname in already_vols:
                continue
            self.volumes.extend([
                {"name": volname,
                 "persistentVolumeClaim": {"claimName": volname,
                                           "accessModes": "ReadOnlyMany"}}])
            self.volume_mounts.extend([
                {"mountPath": "/" + vol,
                 "name": volname}])
        self.log.debug("Volumes: %s" % json.dumps(self.volumes,
                                                  indent=4,
                                                  sort_keys=True))
        self.log.debug("Volume mounts: %s" % json.dumps(self.volume_mounts,
                                                        indent=4,
                                                        sort_keys=True))
        self.image_spec = image_spec
        self.log.debug("Image spec: %s" % json.dumps(image_spec,
                                                     indent=4,
                                                     sort_keys=True))
        self.log.debug("Pod env: %s" % json.dumps(pod_env,
                                                  indent=4,
                                                  sort_keys=True))
        self.log.debug("About to run make_pod()")

        pod = make_pod(
            name=self.pod_name,
            cmd=real_cmd,
            port=self.port,
            image_spec=self.image_spec,
            image_pull_policy=self.image_pull_policy,
            image_pull_secret=self.image_pull_secrets,
            node_selector=self.node_selector,
            run_as_uid=uid,
            run_as_gid=gid,
            fs_gid=fs_gid,
            supplemental_gids=supplemental_gids,
            run_privileged=self.privileged,
            # env is locally-modified
            env=pod_env,
            volumes=self._expand_all(self.volumes),
            volume_mounts=self._expand_all(self.volume_mounts),
            working_dir=self.working_dir,
            labels=labels,
            annotations=annotations,
            cpu_limit=self.cpu_limit,
            cpu_guarantee=self.cpu_guarantee,
            mem_limit=self.mem_limit,
            mem_guarantee=self.mem_guarantee,
            extra_resource_limits=self.extra_resource_limits,
            extra_resource_guarantees=self.extra_resource_guarantees,
            lifecycle_hooks=self.lifecycle_hooks,
            init_containers=self._expand_all(self.init_containers),
            service_account=self.service_account,
            extra_container_config=self.extra_container_config,
            extra_pod_config=self.extra_pod_config,
            extra_containers=self.extra_containers,
        )
        self.log.debug("Got back pod: %r", pod)
        return pod

    def options_from_form(self, formdata=None):
        options = None
        if formdata:
            self.log.debug("Form data: %s", json.dumps(formdata,
                                                       sort_keys=True,
                                                       indent=4))
            options = {}
            if ('kernel_image' in formdata and formdata['kernel_image']):
                options['kernel_image'] = formdata['kernel_image'][0]
            if ('size' in formdata and formdata['size']):
                options['size'] = formdata['size'][0]
            if ('image_tag' in formdata and formdata['image_tag']):
                options['image_tag'] = formdata['image_tag'][0]
            if ('clear_dotlocal' in formdata and formdata['clear_dotlocal']):
                options['clear_dotlocal'] = True
        return options


c.JupyterHub.spawner_class = LSSTSpawner
