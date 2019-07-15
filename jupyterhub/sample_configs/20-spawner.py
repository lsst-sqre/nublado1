"""The spawner is the KubeSpawner, modified to use the options form data.
"""
import base64
import datetime
import json
import namespacedkubespawner
import os
import requests
from kubernetes.client.models import V1PersistentVolumeClaimVolumeSource
from kubernetes.client.models import V1HostPathVolumeSource
from kubespawner.objects import make_pod
from jupyterhubutils import ScanRepo
from tornado import gen
from urllib.error import HTTPError
# Spawn the pod with custom settings retrieved via token additional scope.


class LSSTSpawner(namespacedkubespawner.NamespacedKubeSpawner):
    # class LSSTSpawner(kubespawner.KubeSpawner):
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
    recommended_tag = None
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

    def _options_form_default(self):
        # Make options form by scanning container repository
        title = os.getenv("LAB_SELECTOR_TITLE") or "Container Image Selector"
        owner = os.getenv("LAB_REPO_OWNER") or "lsstsqre"
        repo = os.getenv("LAB_REPO_NAME") or "sciplat-lab"
        host = os.getenv("LAB_REPO_HOST") or "hub.docker.com"
        experimentals = int(os.getenv("PREPULLER_EXPERIMENTALS") or 0)
        dailies = int(os.getenv("PREPULLER_DAILIES") or 3)
        weeklies = int(os.getenv("PREPULLER_WEEKLIES") or 2)
        releases = int(os.getenv("PREPULLER_RELEASES") or 1)
        scanner = ScanRepo(host=host,
                           owner=owner,
                           name=repo,
                           experimentals=experimentals,
                           dailies=dailies,
                           weeklies=weeklies,
                           releases=releases,
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
        if lnames[0].endswith(":recommended"):
            ldescs[0] = self._match_recommended(scanner)
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

    def _match_recommended(self, scanner):
        (lnames, ldescs) = scanner.extract_image_info()
        if self.recommended_tag:
            if self.recommended_tag == "NOTFOUND":
                return ldescs[0]
            if self.recommended_tag in lnames:
                idx = -1
                try:
                    idx = lnames.index(self.recommended_tag)
                except ValueError:
                    pass
                if idx != -1:
                    return "Recommended (%s)" % ldescs[idx]
        # We know lnames[0] ends with ":recommended"
        # ldescs[0] is where we started (probably "Recommended")
        authtok = self._get_auth_token(scanner)
        if not authtok:
            return ldescs[0]
        baseurl = self._get_baseurl(scanner)
        if not baseurl:
            return ldescs[0]
        headers = {}
        if authtok != "NO-AUTH":
            headers = {"Authorization": "Bearer {}".format(authtok)}
        resp = requests.get(baseurl + "manifests/recommended",
                            headers=headers, json=True)
        if resp:
            recjson = resp.json()
        else:
            recjson = {}
        digest = self._get_layers(recjson)
        if not digest:
            return ldescs[0]
        # Now we have the hash of "recommended"; next we match it to
        #  another tag.
        ltags = [x.split(":")[-1] for x in lnames]
        for ltag in ltags:
            if ltag == "recommended":
                continue
            idx = ltags.index(ltag)
            tag = "manifests/" + ltag
            resp = requests.get(baseurl + tag, headers=headers,
                                json=True)
            recjson = resp.json()
            imgdigest = self._get_layers(recjson)
            if imgdigest and imgdigest == digest:
                self.recommended_tag = ltag
                return "Recommended (%s)" % ldescs[idx]
        # Not in our displayed images.  Try the whole list...
        all_tags = []
        try:
            all_tags = scanner.get_all_tags()
        except AttributeError:
            return ldescs[0]
        for tag in all_tags:
            if tag == "recommended":
                continue
            mtag = "manifests/" + tag
            resp = requests.head(baseurl + mtag, headers=headers,
                                 json=True)
            if resp:
                recjson = resp.json()
            else:
                recjson = {}
            imgdigest = self._get_layers(recjson)
            if imgdigest and imgdigest == digest:
                self.recommended_tag = tag
                return "Recommended (%s)" % tag
        # We didn't find it.
        self.recommended_tag = "NOTFOUND"
        return ldescs[0]

    def _get_layers(self, recjson):
        fsl = recjson.get("fsLayers")
        if not fsl:
            return None
        return [x["blobSum"] for x in fsl]

    def _get_auth_token(self, scanner):
        baseurl = self._get_baseurl(scanner)
        if not baseurl:
            return None
        url = baseurl + "manifests/recommended"
        initial_response = requests.get(url)
        sc = initial_response.status_code
        if sc == 200:
            return "NO-AUTH"
        elif sc == 401:
            magicheader = initial_response.headers['Www-Authenticate']
            if magicheader[:7] == "Bearer ":
                hd = {}
                hl = magicheader[7:].split(",")
                for hn in hl:
                    il = hn.split("=")
                    kk = il[0]
                    vv = il[1].replace('"', "")
                    hd[kk] = vv
                if (not hd or "realm" not in hd or "service" not in hd
                        or "scope" not in hd):
                    return None
                endpoint = hd["realm"]
                del hd["realm"]
                tresp = requests.get(endpoint, params=hd, json=True)
                jresp = tresp.json()
                return jresp.get("token")
        else:
            self.log.error("GET %s -> %d" % (url, sc))
            return None

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
                image = self.user_options.get('kernel_image')
                colon = image.find(':')
                if colon > -1:
                    imgname = image[:colon]
                    tag = image[(colon + 1):]
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
        if (image.endswith(":recommended") and self.recommended_tag
                and self.recommended_tag != "NOTFOUND"):
            image = image[:-(len(":recommended"))] + ":" + self.recommended_tag
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
        self.image = image
        s_idx = image.find('/')
        c_idx = image.find(':')
        tag = "latest"
        if s_idx != -1:
            image_name = image[(s_idx + 1):]
            if c_idx > 0:
                image_name = image[(s_idx + 1):c_idx]
                tag = image[(c_idx + 1):].replace('_', '-')
        abbr_pn = image_name
        if image_name == 'sciplat-lab':
            # Saving characters because tags can be long
            abbr_pn = "nb"
        pn_template = abbr_pn + "-{username}-" + tag
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
        '''We're going to return a resource quota spec that allows a max of
        25 (chosen arbitrarily) of the largest-size machines available to
        the user.

        Note that you could get a lot fancier, and check the user group
        memberships to determine what class a user belonged to, or some other
        more-sophisticated-than-one-size-fits-all quota mechanism.
        '''
        self.log.info("Entering get_resource_quota_spec()")
        from kubernetes.client import V1ResourceQuotaSpec
        sizes = self.sizelist
        max_machines = 25 + 1  # Arbitrary (the 25 is intended to represent
        # the number of dask machines, and the 1 is the lab )
        big_multiplier = 2 ** (len(sizes) - 1)
        self.log.info("Max machines %r, multiplier %r" % (max_machines,
                                                          big_multiplier))
        tiny_cpu = os.environ.get('TINY_MAX_CPU') or 0.5
        if type(tiny_cpu) is str:
            tiny_cpu = float(tiny_cpu)
        mem_per_cpu = os.environ.get('MB_PER_CPU') or 2048
        if type(mem_per_cpu) is str:
            mem_per_cpu = int(mem_per_cpu)
        self.log.info("Tiny CPU: %r, Mem per cpu: %r" %
                      (tiny_cpu, mem_per_cpu))
        total_cpu = max_machines * big_multiplier * tiny_cpu
        total_mem = str(int(total_cpu * mem_per_cpu + 0.5)) + "Mi"
        total_cpu = str(int(total_cpu + 0.5))

        self.log.info("Determined quota sizes: CPU %r, mem %r" % (
            total_cpu, total_mem))
        qs = V1ResourceQuotaSpec(
            hard={"limits.cpu": total_cpu,
                  "limits.memory": total_mem})
        self.log.info("Resource quota spec: %r" % qs)
        self._quota = qs.hard
        return qs


c.JupyterHub.spawner_class = LSSTSpawner
