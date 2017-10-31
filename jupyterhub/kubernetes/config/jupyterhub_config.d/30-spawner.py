"""The spawner is the KubeSpawner, modified to use the options form data.
"""
import escapism
import kubespawner
from kubespawner.objects import make_pod
from tornado import gen

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
        auth_state = yield self.user.get_auth_state()
        if auth_state and "id" in auth_state:
            if auth_state["id"] != self.user.id:
                self.log.info("Updating userid from %d to %d" %
                              (self.user.id, auth_state["id"]))
                #self.user.id = auth_state["id"]
                # I think this messes up auth_token.
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
