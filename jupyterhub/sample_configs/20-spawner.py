"""The spawner is the KubeSpawner, modified to use the options form data.
"""
import base64
import datetime
import json
import namespacedkubespawner
import os
import shlex
from kubernetes.client.models import V1PersistentVolumeClaimVolumeSource
from kubernetes.client.models import V1HostPathVolumeSource
from kubernetes.client.models import V1ConfigMap
from kubespawner.objects import make_pod
from jupyterhubutils import SingletonScanner
from time import sleep
from tornado import gen


class LSSTSpawner(namespacedkubespawner.NamespacedKubeSpawner):
    """Spawner to use our custom environment settings as reflected through
    auth_state."""

    # A couple of fields to use when constructing a custom spawner form
    _sizemap = {}
    sizelist = ["tiny", "small", "medium", "large"]
    # In our LSST setup, there is a "provisionator" user, uid/gid 769,
    #  that is who we should start as.
    uid = 769
    gid = 769
    # The fields need to be defined; we don't use them.
    fs_gid = None
    supplemental_gids = []
    extra_labels = {}
    if os.getenv("RESTRICT_LAB_SPAWN"):
        extra_labels["jupyterlab"] = "ok"
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
        service_account = "dask"
    # Change some defaults.
    delete_namespace_on_stop = True
    delete_namespaced_pvs_on_stop = True
    # To add quota support:
    #  set enable_namespace_quotas = True
    # and then add a method:
    #  self.get_resource_quota_spec()
    #   which should return a kubernetes.client.V1ResourceQuotaSpec
    enable_namespace_quotas = True
    # stash quota values to pass to spawned environment
    _quota = {}
    _custom_resources = {}
    _scanner = None

    def _options_form_default(self):
        # Make options form by scanning container repository
        title = os.getenv("LAB_SELECTOR_TITLE") or "Container Image Selector"
        owner = os.getenv("LAB_REPO_OWNER") or "lsstsqre"
        name = os.getenv("LAB_REPO_NAME") or "sciplat-lab"
        host = os.getenv("LAB_REPO_HOST") or "hub.docker.com"
        experimentals = int(os.getenv("PREPULLER_EXPERIMENTALS", 0))
        dailies = int(os.getenv("PREPULLER_DAILIES", 3))
        weeklies = int(os.getenv("PREPULLER_WEEKLIES", 2))
        releases = int(os.getenv("PREPULLER_RELEASES", 1))
        cachefile = os.getenv("HOME") + "/repo-cache.json"
        debug = False
        if os.getenv("DEBUG"):
            debug = True
        scanner = SingletonScanner(host=host,
                                   owner=owner,
                                   name=name,
                                   experimentals=experimentals,
                                   dailies=dailies,
                                   weeklies=weeklies,
                                   releases=releases,
                                   cachefile=cachefile,
                                   debug=debug)
        self._scanner = scanner
        self._sync_scan()
        lnames, ldescs = scanner.extract_image_info()
        if not lnames or len(lnames) < 2:
            return ""
        resmap = scanner.get_all_scan_results()
        all_tags = list(resmap.keys())
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
        optform += "<select name=\"image_tag\""
        optform += "onchange=\"document.forms['spawn_form']."
        optform += "kernel_image.value='%s'\">\n" % custtag
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
        size_index = self._get_size_index()
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
        optform += "<td><tr>\n"
        # Add 'noninteractive box' and field
        optform += "<input type=\"checkbox\" name=\"noninteractive\""
        optform += " onclick=\"ShowHideCommand(this)\""
        optform += " value=\"true\">"
        optform += "<div id=\"ni-cmd-div\""
        optform += " style=\"display:none;\">\n"
        optform += "Command: <input type=\"text\" name=\"ni_cmd\" width=80"
        optform += " value=\"/bin/true\">"
        optform += "</div>\n"
        optform += "</td></tr>\n"
        optform += "      </table>\n"
        optform += "<hr />\n"
        optform += "Menu updated at %s<br />\n" % nowstr
        optform += "<script>\n"
        optform += "function ShowHideCommand(d)\n"
        optform += "{\n"
        optform += "  var cmdline = document.getElementById(\"ni-cmd-div\")\n"
        optform += "  if ( d.checked == true )\n"
        optform += "  {\n"
        optform += "    cmdline.style.display = \"block\";\n"
        optform += "  }\n"
        optform += "  else\n"
        optform += "  {\n"
        optform += "    cmdline.style.display = \"none\";\n"
        optform += "  }\n"
        optform += "}\n"
        return optform

    def _sync_scan(self):
        scanner = self._scanner
        delay_interval = 5
        max_delay = 300
        delay = 0
        while scanner.last_updated == datetime.datetime(1970, 1, 1):
            self.log.warning("Scan results not available yet; sleeping " +
                             "{}s ({}s so far).".format(delay_interval,
                                                        delay))
            sleep(delay_interval)
            delay = delay + delay_interval
            if delay >= max_delay:
                errstr = ("Scan results did not become available in " +
                          "{}s.".format(max_delay))
                raise RuntimeError(errstr)

    def _make_sizemap(self):
        sizes = self.sizelist
        tiny_cpu = os.environ.get('TINY_MAX_CPU') or 0.5
        if type(tiny_cpu) is str:
            tiny_cpu = float(tiny_cpu)
        mem_per_cpu = os.environ.get('MB_PER_CPU') or 2048
        if type(mem_per_cpu) is str:
            mem_per_cpu = int(mem_per_cpu)
        cpu = tiny_cpu
        for sz in sizes:
            mem = mem_per_cpu * cpu
            self._sizemap[sz] = {"cpu": cpu,
                                 "mem": mem}
            desc = sz.title() + " (%.2f CPU, %dM RAM)" % (cpu, mem)
            self._sizemap[sz]["desc"] = desc
            cpu = cpu * 2
        # Clean up if list of sizes changed.
        for esz in self._sizemap:
            if esz not in sizes:
                del self._sizemap[esz]

    def _get_size_index(self):
        sizes = list(self._sizemap.keys())
        si = self._custom_resources.get(
            "size_index") or os.environ.get('SIZE_INDEX') or 1
        size_index = int(si)
        if size_index >= len(sizes):
            size_index = len(sizes) - 1
        return size_index

    def _set_custom_user_resources(self):
        if self._custom_resources:
            return
        rfile = "/opt/lsst/software/jupyterhub/resources/resourcemap.json"
        resources = {
            "size_index": 0,
            "cpu_quota": 0,
            "mem_quota": 0
        }
        try:
            gnames = self._get_user_groupnames()
            uname = self.user.name
            with open(rfile, "r") as rf:
                resmap = json.load(rf)
            for resdef in resmap:
                apply = False
                if resdef.get("disabled"):
                    continue
                candidate = resdef.get("resources")
                if not candidate:
                    continue
                self.log.debug(
                    "Considering candidate resource map {}".format(resdef))
                ruser = resdef.get("user")
                rgroup = resdef.get("group")
                if ruser and ruser == uname:
                    self.log.debug("User resource map match.")
                    apply = True
                if rgroup and rgroup in gnames:
                    self.log.debug("Group resource map match.")
                    apply = True
                if apply:
                    for fld in ["size_index", "cpu_quota", "mem_quota"]:
                        vv = candidate.get(fld)
                        if vv and vv > resources[fld]:
                            resources[fld] = vv
                    self.log.info(
                        "Setting custom resources '{}'".format(resources))
                    self._custom_resources = resources
        except Exception as exc:
            self.log.error(
                "Custom resource check got exception '{}'".format(exc))

    def _get_user_groupnames(self):
        try:
            return self.authenticator.groups
        except AttributeError:
            self.log.error("Authenticator object has no groups attribute.")
            return []

    def _get_baseurl(self, scanner):
        host = scanner.host
        if host == "hub.docker.com":
            host = "registry.hub.docker.com"
        protocol = "https"
        if scanner.insecure:
            protocol = "http"
        owner = scanner.owner
        name = scanner.name
        if not owner or not name:
            if scanner.path:
                pl = scanner.path.split('/')
                owner = pl[3]
                name = pl[4]
        if not owner or not name:
            return None
        baseurl = protocol + "://" + host + "/v2/" + owner + "/" + name + "/"
        return baseurl

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
            supplemental_gids = yield gen.maybe_future(
                self.supplemental_gids(self))
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
            self.service_account = 'dask'

        pod_name = self.pod_name
        image = (self.image or
                 os.getenv("LAB_IMAGE") or
                 "lsstsqre/sciplat-lab:latest")
        image_name = image
        tag = "latest"
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
        noninteractive = False
        ni_cmd = None
        if self.user_options:
            self.log.debug("user_options: %s" % json.dumps(self.user_options,
                                                           sort_keys=True,
                                                           indent=4))
            if self.user_options.get('kernel_image'):
                image = self.user_options.get('kernel_image')
                colon = image.find(':')
                if colon > -1:
                    imgname = image[:colon]
                    tag = image[(colon + 1):]
                    if tag == "recommended" or tag.startswith("latest"):
                        self.log.info("Resolving tag '{}'".format(tag))
                        if self._scanner:
                            qtag = self._scanner.resolve_tag(tag)
                            if qtag:
                                tag = qtag
                                image = imgname + ":" + tag
                                image_name = image
                            else:
                                self.log.warning(
                                    "Failed to resolve tag '{}'".format(tag))
                    self.log.debug("Image name: %s ; tag: %s" % (imgname, tag))
                    if tag == "__custom":
                        cit = self.user_options.get('image_tag')
                        if cit:
                            image = imgname + ":" + cit
                image_name = image
                self.log.info("Replacing image from options form: %s" % image)
                size = self.user_options.get('size')
                if size:
                    image_size = self._sizemap[size]
                clear_dotlocal = self.user_options.get('clear_dotlocal')
                noninteractive = self.user_options.get('noninteractive')
                if noninteractive:
                    ni_cmd = self.user_options.get('ni_cmd')
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
        self.log.debug("Image: {}".format(image))
        self.image = image
        # Parse the image name + tag
        i_l = image.split("/")
        if len(i_l) == 1:
            repo_tag = i_l[0]
        else:
            repo_tag = i_l[1]
        repo = repo_tag.split(":")[0]
        rt_tag = tag.replace('_', '-')
        abbr_pn = repo
        if repo == 'sciplat-lab':
            # Saving characters because tags can be long
            abbr_pn = "nb"
        pn_template = abbr_pn + "-{username}-" + rt_tag
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
        external_hub_url = os.getenv('EXTERNAL_HUB_URL')
        hub_route = os.getenv('HUB_ROUTE')
        while (hub_route.endswith('/') and hub_route != "/"):
            hub_route = hub_route[:-1]
        if not external_hub_url:
            oauth_callback = os.getenv('OAUTH_CALLBACK_URL')
            endstr = "/hub/oauth_callback"
            if oauth_callback and oauth_callback.endswith(endstr):
                external_hub_url = oauth_callback[:-len(endstr)]
        # Guaranteed external endpoints
        pod_env['EXTERNAL_URL'] = external_hub_url
        pod_env['EXTERNAL_HUB_URL'] = external_hub_url
        external_instance_url = os.getenv('EXTERNAL_INSTANCE_URL')
        if not external_instance_url:
            if external_hub_url.endswith(hub_route):
                external_instance_url = external_hub_url[:-len(hub_route)]
        pod_env['EXTERNAL_INSTANCE_URL'] = external_instance_url
        if os.getenv('DEBUG'):
            pod_env['DEBUG'] = os.getenv('DEBUG')
        if clear_dotlocal:
            pod_env['CLEAR_DOTLOCAL'] = "true"
        if noninteractive:
            pod_env['NONINTERACTIVE'] = "true"
            self._add_ni_configmap(ni_cmd)
        # Add service routes
        # Check if we need trailing slash anymore for firefly
        hub_route = os.getenv('HUB_ROUTE') or "/nb"
        firefly_route = os.getenv('FIREFLY_ROUTE') or "/firefly/"
        js9_route = os.getenv('JS9_ROUTE') or "/js9"
        api_route = os.getenv('API_ROUTE') or "/api"
        tap_route = os.getenv('TAP_ROUTE') or "/api/tap"
        soda_route = os.getenv('SODA_ROUTE') or "/api/image/soda"
        pod_env['HUB_ROUTE'] = hub_route
        pod_env['FIREFLY_ROUTE'] = firefly_route
        pod_env['JS9_ROUTE'] = js9_route
        pod_env['API_ROUTE'] = api_route
        pod_env['TAP_ROUTE'] = tap_route
        pod_env['SODA_ROUTE'] = soda_route
        # Optional external endpoints
        for i in ['firefly', 'js9', 'api', 'tap', 'soda']:
            envvar = 'EXTERNAL_' + i.upper() + '_URL'
            if os.getenv(envvar):
                pod_env[envvar] = os.getenv(envvar)
        auto_repo_urls = os.getenv('AUTO_REPO_URLS')
        if auto_repo_urls:
            pod_env['AUTO_REPO_URLS'] = auto_repo_urls

        vollist = self._get_volume_list()
        self._splice_volumes(vollist)

        pod_env['DASK_VOLUME_B64'] = self._get_dask_volume_b64()
        if self._quota:
            pod_env['NAMESPACE_CPU_LIMIT'] = self._quota["limits.cpu"]
            nmlimit = self._quota["limits.memory"]
            if nmlimit[-2:] == "Mi":
                # Not technically correct, but matches mem_limit
                nmlimit = nmlimit[:-2] + "M"
            pod_env['NAMESPACE_MEM_LIMIT'] = nmlimit
        pod_env['CPU_LIMIT'] = str(cpu_limit)
        pod_env['MEM_LIMIT'] = str(mem_limit)
        self.image = image
        self.log.debug("Image: %s" % json.dumps(image,
                                                indent=4,
                                                sort_keys=True))
        self.log.debug("Pod env: %s" % json.dumps(pod_env,
                                                  indent=4,
                                                  sort_keys=True))
        if not pod_env.get("EXTERNAL_UID"):
            raise ValueError("EXTERNAL_UID is not set!")
        self.log.debug("About to run make_pod()")

        pod = make_pod(
            name=self.pod_name,
            cmd=real_cmd,
            port=self.port,
            image=self.image,
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
            node_affinity_preferred=self.node_affinity_preferred,
            node_affinity_required=self.node_affinity_required,
            pod_affinity_preferred=self.pod_affinity_preferred,
            pod_affinity_required=self.pod_affinity_required,
            pod_anti_affinity_preferred=self.pod_anti_affinity_preferred,
            pod_anti_affinity_required=self.pod_anti_affinity_required,
            priority_class_name=self.priority_class_name,
            logger=self.log,
        )
        return pod

    def _get_dask_volume_b64(self):
        vols = self.volumes
        vmts = self.volume_mounts
        rstr = ""
        dyaml = "Constructing dask yaml for "
        if vmts:
            rstr += "    volumeMounts:\n"
            for vm in vmts:
                self.log.debug(dyaml + vm["name"])
                rstr += "      - name: {}\n".format(vm["name"])
                rstr += "        mountPath: {}\n".format(vm["mountPath"])
                if vm.get("readOnly"):
                    rstr += "        readOnly: true\n"
        if vols:
            rstr += "  volumes:\n"
            for vol in vols:
                self.log.debug(dyaml + vol["name"])
                rstr += "    - name: {}\n".format(vol["name"])
                if vol.get("persistent_volume_claim"):
                    rstr += "      persistentVolumeClaim:\n"
                    pvc = vol.get("persistent_volume_claim")
                    rstr += "        claimName: {}\n".format(pvc.claim_name)
                    if hasattr(pvc, "read_only") and pvc.read_only:
                        rstr += "        accessMode: ReadOnlyMany\n"
                    else:
                        rstr += "        accessMode: ReadWriteMany\n"
                elif vol.get("nfs"):
                    nfs = vol.get("nfs")
                    # Just a dict
                    self.log.debug("NFS: %r" % nfs)
                    rstr += "      nfs:\n"
                    rstr += "        server: {}\n".format(nfs["server"])
                    rstr += "        path: {}\n".format(nfs["path"])
                    rstr += "        accessMode: {}\n".format(
                        nfs["accessModes"][0])
                elif vol.get("host_path"):
                    hp = vol.get("host_path")
                    self.log.debug("HostPath: %r" % hp)
                    rstr += "      hostPath:\n"
                    rstr += "        type: Directory\n"
                    rstr += "        path: {}\n".format(hp.path)
        self.log.debug("Dask yaml:\n%s" % rstr)
        benc = base64.b64encode(rstr.encode('utf-8')).decode('utf-8')
        return benc

    def _get_volume_list(self):
        """Override this in a subclass if you like.
        """
        vollist = []
        config = []
        cfile = "/opt/lsst/software/jupyterhub/mounts/mountpoints.json"
        with open(cfile, "r") as fp:
            config = json.load(fp)
        for mtpt in config:
            self.log.debug("mtpt: %r" % mtpt)
            mountpoint = mtpt["mountpoint"]  # Fatal error if it doesn't exist
            if mtpt.get("disabled"):
                self.log.debug("Skipping disabled mountpoint %s" % mountpoint)
                continue
            if mountpoint[0] != "/":
                mountpoint = "/" + mountpoint
            host = mtpt.get("fileserver-host") or os.getenv(
                "EXTERNAL_FILESERVER_IP") or os.getenv(
                "FILESERVER_SERVICE_HOST")
            export = mtpt.get("fileserver-export") or (
                "/exports" + mountpoint)
            mode = (mtpt.get("mode") or "ro").lower()
            options = mtpt.get("options")  # Doesn't work yet.
            k8s_vol = mtpt.get("kubernetes-volume")
            hostpath = mtpt.get("hostpath")
            vollist.append({
                "mountpoint": mountpoint,
                "hostpath": hostpath,
                "k8s_vol": k8s_vol,
                "host": host,
                "export": export,
                "mode": mode,
                "options": options
            })
        self.log.debug("Volume list: %r" % vollist)
        return vollist

    def _get_volume_name_for_mountpoint(self, mountpoint):
        podname = self.pod_name
        namespace = self.get_user_namespace()
        mtname = mountpoint[1:].replace("/", "-")
        return "{}-{}-{}".format(mtname, namespace, podname)

    def _splice_volumes(self, vollist):
        namespace = self.get_user_namespace()
        already_vols = []
        if self.volumes:
            already_vols = [x["name"] for x in self.volumes]
            self.log.debug("Already_vols: %r" % already_vols)
        for vol in vollist:
            mountpoint = vol["mountpoint"]
            if not mountpoint:
                self.log.error(
                    "Mountpoint not specified for volume '{}'!".format(vol)
                )
                continue
            volname = self._get_volume_name_for_mountpoint(mountpoint)
            shortname = mountpoint[1:].replace("/", "-")
            if shortname in already_vols:
                self.log.info(
                    "Volume '{}' already exists for pod.".format(volname))
                continue
            k8s_vol = vol["k8s_vol"]
            hostpath = vol["hostpath"]
            if k8s_vol and not hostpath:
                # If hostpath is set, k8s_vol should NOT be, but...
                # Create shadow PV and namespaced PVC for volume
                kvol = self._get_nfs_volume(k8s_vol)
                ns_vol = self._replicate_nfs_pv_with_suffix(
                    kvol, namespace)
                self._create_pvc_for_pv(ns_vol)
            mode = "ReadOnlyMany"
            vmro = True
            if vol["mode"] == "rw":
                mode = "ReadWriteMany"
                vmro = False
            vvol = {
                "name": shortname,
            }
            if hostpath:
                vsrc = V1HostPathVolumeSource(
                    path=hostpath,
                    type="Directory"
                )
                vvol["host_path"] = vsrc
            elif k8s_vol:
                pvcvs = V1PersistentVolumeClaimVolumeSource(
                    claim_name=ns_vol.metadata.name,
                    read_only=vmro
                )
                vvol["persistent_volume_claim"] = pvcvs
            else:
                vvol["nfs"] = {
                    "server": vol["host"],
                    "path": vol["export"],
                    "accessModes": [mode]
                }

            self.volumes.append(vvol)
            options = vol.get("options")
            if options:
                optlist = options.split(',')
                # This does not work.
                # To get NFS with mount_options, you need to specify the
                #  'kubernetes-volume' parameter and create your PV with the
                #  appropriate volumes in the first place.
                vvol["nfs"]["mount_options"] = optlist
            vmount = {
                "name": shortname,
                "mountPath": mountpoint
            }
            if vmro:
                vmount["readOnly"] = True
            self.volume_mounts.append(vmount)

    def _add_ni_configmap(self, cmdline):
        if not cmdline:
            cmdline = "/bin/true"
        cmds = shlex.split(cmdline)
        cmds_s = json.dumps(cmds)
        cmdict = {"type": "cmd",
                  "command": cmds_s}
        cmobj = V1ConfigMap(data=cmdict)
        namespace = self.get_user_namespace()
        # FIXME
        self.api.create_namespaced_config_map(namespace, cmobj)

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

    def get_resource_quota_spec(self):
        '''We're going to return a resource quota spec that checks whether we
        have a custom resource map and uses that information.  If we do not
        then our default quota allows a maximum of MAX_DASK_WORKERS or
        25 (chosen arbitrarily) of the largest-size machines available to the
        user.

        Note that you could get a lot fancier, and check the user group
        memberships to determine what class a user belonged to, or some other
        more-sophisticated-than-one-size-fits-all quota mechanism.
        '''
        self.log.info("Entering get_resource_quota_spec()")
        from kubernetes.client import V1ResourceQuotaSpec
        self.log.info("Calculating default resource quotas.")
        sizes = self.sizelist
        max_dask_workers = os.environ.get('MAX_DASK_WORKERS') or 25
        max_machines = int(max_dask_workers) + 1  # (the 1 is the Lab)
        big_multiplier = 2 ** (len(sizes) - 1)
        tiny_cpu = os.environ.get('TINY_MAX_CPU') or 0.5
        if type(tiny_cpu) is str:
            tiny_cpu = float(tiny_cpu)
        mem_per_cpu = os.environ.get('MB_PER_CPU') or 2048
        if type(mem_per_cpu) is str:
            mem_per_cpu = int(mem_per_cpu)
        total_cpu = max_machines * big_multiplier * tiny_cpu
        total_mem = str(int(total_cpu * mem_per_cpu + 0.5)) + "Mi"
        total_cpu = str(int(total_cpu + 0.5))
        self.log.debug("Default quota sizes: CPU %r, mem %r" % (
            total_cpu, total_mem))
        if self._custom_resources:
            self.log.debug("Have custom resources.")
            cpuq = self._custom_resources.get("cpu_quota")
            if cpuq:
                self.log.debug("Overriding CPU quota.")
                total_cpu = str(cpuq)
            memq = self._custom_resources.get("mem_quota")
            if memq:
                self.log.debug("Overriding memory quota.")
                total_mem = str(memq) + "Mi"
        self.log.info("Determined quota sizes: CPU %r, mem %r" % (
            total_cpu, total_mem))
        qs = V1ResourceQuotaSpec(
            hard={"limits.cpu": total_cpu,
                  "limits.memory": total_mem})
        self.log.info("Resource quota spec: %r" % qs)
        self._quota = qs.hard
        return qs


c.JupyterHub.spawner_class = LSSTSpawner
