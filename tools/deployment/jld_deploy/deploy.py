#!/usr/bin/env python3
"""This is a wrapper around a JupyterLabDeployment class.  The class,
at the moment, assumes the following:

1) Deployment is to Google Kubernetes Engine.  You have chosen a cluster name
    and optionally a namespace.
2) Your DNS zone for your external endpoint is hosted in Route 53 and you
    have chosen a FQDN for your application.
3) You are running this from an execution context where gcloud, kubectl,
    and aws have all been set up to run authenticated from the command
    line.
4) At least your external endpoint TLS certs are already generated and
    exist on the local filesystem.  If you need certificates for ELK
    stack communication, those must also be present on the local filesystem.
5) You are using GitHub or CILogon OAuth for your authentication, and you
    have created an OAuth application Client ID, Client Secret, and a client
    callback that is 'https://fqdn.of.jupyterlab.demo/hub/oauth_callback'.
    If you are using GitHub as your OAuth2 provider, you must also specify
    a list of GitHub organizations, to at least one of which any authenticated
    user must belong.
6) Either all of this information has been encoded in a YAML file that you
    reference with the -f switch during deployment, or it's in a series of
    environment variables starting with "JLD_", or you enter it at a
    terminal prompt.
    - If you specify a directory for TLS certificates, the
      certificate, key, and root chain files must be named "cert.pem",
      "key.pem", and "chain.pem" respectively.  If you already have a
      DH Params file, it should be called "dhparam.pem" in the same directory.
    - If present in that directory, the ELK certificates must be
      "beats_cert.pem", "beats_key.pem", and
      "beats_ca.pem" for certificate, key, and certificate authority
      respectively.

Obvious future enhancements are to make this work with a wider variety of
Kubernetes and DNS providers.

It is capable of deploying and undeploying a JupyterLab Demo environment,
or of generating a set of Kubernetes configuration files suitable for
editing and then deploying from this tool.
"""
import argparse
import base64
import datetime
import dns.resolver
import fnmatch
import json
import logging
import os
import os.path
import shutil
import subprocess
import sys
import tempfile
import time
import yaml
from contextlib import contextmanager
from jinja2 import Template

if sys.version_info < (3, 5):
    raise RuntimeError("Python >= 3.5 is required.")

EXECUTABLES = ["gcloud", "kubectl", "aws"]
DEFAULT_GKE_ZONE = "us-central1-a"
DEFAULT_GKE_MACHINE_TYPE = "n1-standard-2"
DEFAULT_GKE_NODE_COUNT = 3
DEFAULT_GKE_LOCAL_VOLUME_SIZE_GB = 200
DEFAULT_VOLUME_SIZE_GB = 20
ENVIRONMENT_NAMESPACE = "JLD_"
ME = os.path.realpath(__file__)
OAUTH_DEFAULT_PROVIDER = "github"
REQUIRED_PARAMETER_NAMES = ["kubernetes_cluster_name",
                            "hostname"]
REQUIRED_DEPLOYMENT_PARAMETER_NAMES = REQUIRED_PARAMETER_NAMES + [
    "oauth_client_id",
    "oauth_secret",
    "tls_cert",
    "tls_key",
    "tls_root_chain",
    "allowed_groups"
]
PARAMETER_NAMES = REQUIRED_DEPLOYMENT_PARAMETER_NAMES + [
    "github_organization_whitelist",
    "cilogon_group_whitelist",
    "oauth_provider",
    "tls_dhparam",
    "kubernetes_cluster_namespace",
    "gke_zone",
    "gke_node_count",
    "gke_machine_type",
    "gke_local_volume_size_gigabytes",
    "volume_size_gigabytes",
    "session_db_url",
    "shipper_name",
    "rabbitmq_pan_password",
    "rabbitmq_target_host",
    "rabbitmq_target_vhost",
    "external_fileserver_ip",
    "firefly_admin_password",
    "prepuller_image_list",
    "prepuller_no_scan",
    "prepuller_repo",
    "prepuller_owner",
    "prepuller_image_name",
    "prepuller_dailies",
    "prepuller_weeklies",
    "prepuller_releases",
    "prepuller_insecure",
    "prepuller_port",
    "prepuller_sort_field",
    "prepuller_command",
    "prepuller_namespace",
    "lab_selector_title",
    "lab_idle_timeout",
    "lab_cpu_limit",
    "lab_mem_limit",
    "lab_cpu_guarantee",
    "lab_mem_guarantee",
    "debug"]


class JupyterLabDeployment(object):
    """JupyterLab Deployment object.
    """
    directory = None
    components = ["logstashrmq", "filebeat", "fileserver", "fs-keepalive",
                  "firefly", "prepuller", "jupyterhub", "nginx"]
    params = None
    yamlfile = None
    original_context = None
    enable_firefly = False
    enable_prepuller = True
    enable_logging = False
    existing_cluster = False
    b64_cache = {}
    executables = {}
    srcdir = None
    disklist = []
    _activedisk = None

    def __init__(self, yamlfile=None, params=None, directory=None,
                 disable_prepuller=False, existing_cluster=False,
                 existing_namespace=False, config_only=False,
                 temporary=False):
        self._check_executables(EXECUTABLES)
        if yamlfile:
            self.yamlfile = os.path.realpath(yamlfile)
        self.existing_cluster = existing_cluster
        self.existing_namespace = existing_namespace
        self.temporary = temporary
        self.directory = directory
        if self.directory:
            self.directory = os.path.realpath(self.directory)
            self.temporary = False
        self.config_only = config_only
        self.params = params
        if disable_prepuller:
            self.enable_prepuller = False

    @contextmanager
    def kubecontext(self):
        """Save and restore original Kubernetes context.
        """
        self._check_authentication()
        savec = ["kubectl", "config", "current-context"]
        rc = self._run(savec, capture=True, check=False)
        if rc.stdout:
            self.original_context = rc.stdout.decode('utf-8').strip()
        yield
        if self.original_context:
            restorec = ["kubectl", "config",
                        "use-context", self.original_context]
            self._run(restorec, check=False)

    def _check_authentication(self):
        """We also set the AWS zone id from this: if the hostname is not
        in an AWS hosted zone, we want to fail sooner rather than later.
        """
        logging.info("Checking authentication.")
        cmd = "gcloud info --format yaml".split()
        rc = self._run(cmd, capture=True)
        if rc.returncode == 0:
            gstruct = yaml.load(rc.stdout.decode('utf-8'))
            acct = gstruct["config"]["account"]
            if not acct:
                raise RuntimeError("gcloud not logged in; " +
                                   "try 'gcloud init'")
        self.params["zoneid"] = self._get_aws_zone_id()

    def _get_aws_zone_id(self):
        """Grab the zone ID from the domain determined from the hostname.
        """
        hostname = self.params["hostname"]
        domain = '.'.join(hostname.split('.')[1:])
        try:
            zp = self._run(["aws", "route53", "list-hosted-zones",
                            "--output", "json"],
                           capture=True)
            zones = json.loads(zp.stdout.decode('utf-8'))
            zlist = zones["HostedZones"]
            for z in zlist:
                if z["Name"] == domain + ".":
                    zonename = z["Id"]
                    zone_components = zonename.split('/')
                    zoneid = zone_components[-1]
                    return zoneid
            raise RuntimeError("No zone found")
        except Exception as e:
            raise RuntimeError(
                "Could not determine AWS zone id for %s: %s" % (domain,
                                                                str(e)))

    def _check_executables(self, proglist):
        """Resolve executables we run via subprocess.
        """
        for p in proglist:
            rc = _which(p)
            if not rc:
                raise ValueError("%s not on search path!" % p)
            self.executables[p] = rc

    def _set_params(self):
        """Load parameters from YAML file.
        """
        if not self.params:
            with open(self.yamlfile, 'r') as f:
                self.params = yaml.load(f)
            for p in self.params:
                if p not in PARAMETER_NAMES:
                    logging.warn("Unknown parameter '%s'!" % p)

    def _empty_param(self, key):
        """False only if key exists and has truthy value.
        """
        if key not in self.params or not self.params[key]:
            return True
        return False

    def _any_empty(self, keylist):
        """True if any empty params in list.
        """
        for key in keylist:
            if self._empty_param(key):
                return True
        return False

    def _run(self, args, directory=None, capture=False,
             capture_stderr=False, check=True):
        """Convenience wrapper around subprocess.run.  Requires Python 3.5
        for that reason.
        """
        stdout = None
        stderr = None
        if capture:
            stdout = subprocess.PIPE
        if capture_stderr:
            stderr = subprocess.PIPE
        if not directory:
            directory = self.directory or os.getcwd()
        with _wd(directory):
            exe = args[0]
            fqexe = self.executables.get(exe)
            if fqexe:
                args[0] = fqexe
            self._logcmd(args)
            rc = subprocess.run(args, check=check, stdout=stdout,
                                stderr=stderr)
            return rc

    def _get_cluster_info(self):
        """Get cluster name and namespace.
        """
        if self._empty_param('kubernetes_cluster_name'):
            if not self._empty_param('hostname'):
                hname = self.params["hostname"]
                cname = hname.translate({ord('.'): '-'})
                logging.warn("Using default derived cluster name '%s'" %
                             cname)
                self.params["kubernetes_cluster_name"] = cname
            else:
                raise ValueError("'kubernetes_cluster_name' must be set, " +
                                 "either explicitly or from 'hostname'.")
        if self._empty_param('kubernetes_cluster_namespace'):
            hname = self.params["hostname"]
            nspace = hname.split('.')[0]
            logging.info("Using default cluster namespace '%s'." % nspace)
            self.params["kubernetes_cluster_namespace"] = nspace
        if self._empty_param('gke_zone'):
            logging.info("Using default gke_zone '%s'." % DEFAULT_GKE_ZONE)
            self.params["gke_zone"] = DEFAULT_GKE_ZONE

    def _validate_deployment_params(self):
        """Verify that we have what we need, and get sane defaults for things
        that can be defaulted.
        """
        self._get_cluster_info()
        if self._empty_param("allowed_groups"):
            if not self._empty_param("oauth_provider"):
                if self.params["oauth_provider"] == "cilogon":
                    self.params["allowed_groups"] = self.params.get(
                        "cilogon_group_whitelist")
                else:
                    self.params["allowed_groups"] = self.params.get(
                        "github_organization_whitelist")
        if self._any_empty(REQUIRED_PARAMETER_NAMES):
            raise ValueError("All parameters '%s' must be specified!" %
                             str(REQUIRED_PARAMETER_NAMES))
        del self.params["allowed_groups"]
        if self._empty_param('volume_size_gigabytes'):
            logging.warn("Using default volume size: 20GiB")
            self.params["volume_size_gigabytes"] = DEFAULT_VOLUME_SIZE_GB
        if self.params["volume_size_gigabytes"] < 1:
            raise ValueError("Shared volume must be at least 1 GiB!")
        if self._empty_param('gke_machine_type'):
            self.params['gke_machine_type'] = DEFAULT_GKE_MACHINE_TYPE
        if self._empty_param('gke_node_count'):
            self.params['gke_node_count'] = DEFAULT_GKE_NODE_COUNT
        if self._empty_param('gke_local_volume_size_gigabytes'):
            self.params['gke_local_volume_size_gigabytes'] = \
                DEFAULT_GKE_LOCAL_VOLUME_SIZE_GB
        if self._empty_param('oauth_provider'):
            self.params['oauth_provider'] = OAUTH_DEFAULT_PROVIDER
        if self.params['oauth_provider'] != OAUTH_DEFAULT_PROVIDER:
            if self._empty_param('github_organization_whitelist'):
                # Not required if we aren't using GitHub.
                self.params['github_organization_whitelist'] = "dummy"
        if self.params['oauth_provider'] != "cilogon":
            if self._empty_param('cilogon_group_whitelist'):
                # Not required if we aren't using CILogon.
                self.params['cilogon_group_whitelist'] = "dummy"
        if self._empty_param('debug'):
            self.params['debug'] = ''  # Empty is correct
        # Rely on defaults by setting environment in prepuller to
        #  empty for unused parameters
        for pname in ['prepuller_image_list', 'prepuller_no_scan',
                      'prepuller_repo', 'prepuller_owner',
                      'prepuller_image_name', 'prepuller_dailies',
                      'prepuller_weeklies', 'prepuller_releases',
                      'prepuller_port', 'prepuller_sort_field',
                      'prepuller_command', 'prepuller_namespace']:
            if self._empty_param(pname):
                self.params[pname] = ''
        if self._empty_param('lab_selector_title'):
            self.params['lab_selector_title'] = "LSST Stack Selector"
        if self._empty_param('lab_idle_timeout'):
            self.params['lab_idle_timeout'] = "43200"  # string, not int
        if self._empty_param('lab_mem_limit'):
            self.params['lab_mem_limit'] = "3G"
        if self._empty_param('lab_cpu_limit'):
            self.params['lab_cpu_limit'] = "2.0"
        if self._empty_param('lab_mem_guarantee'):
            self.params['lab_mem_guarantee'] = "512M"
        if self._empty_param('lab_cpu_guarantee'):
            self.params['lab_cpu_guarantee'] = "0.5"
        return

    def _normalize_params(self):
        """Some parameters are calculated.  Do that.
        """
        sz = int(self.params['volume_size_gigabytes'])
        self.params['volume_size'] = str(sz) + "Gi"
        if sz > 1:
            nfs_sz = str(int(0.95 * sz)) + "Gi"
        else:
            nfs_sz = "950Mi"
        self.params['nfs_volume_size'] = nfs_sz
        logging.info("Volume size: %s / NFS volume size: %s" %
                     (self.params['volume_size'],
                      self.params['nfs_volume_size']))
        self.params[
            'oauth_callback_url'] = ("https://%s/hub/oauth_callback" %
                                     self.params['hostname'])
        self.params["github_organization_whitelist"] = ','.join(
            self.params["github_organization_whitelist"])
        self.params["cilogon_group_whitelist"] = ','.join(
            self.params["cilogon_group_whitelist"])
        if not self._empty_param("prepuller_image_list"):
            self.params["prepuller_image_list"] = ",".join(
                self.params["prepuller_image_list"])
        self._check_optional()

    def _check_optional(self):
        """Look for optional variables and decide whether we are setting
        up logging and firefly based on those.  Also decide if we need to
        create dhparam.pem and if so how large it needs to be.
        """
        # We give all of these empty string values to make the
        #  templating logic easier.
        if self._empty_param('firefly_admin_password'):
            self.params['firefly_admin_password'] = ''
        else:
            self.enable_firefly = True
        logging_vars = ['rabbitmq_pan_password',
                        'rabbitmq_target_host',
                        'rabbitmq_target_vhost',
                        'log_shipper_name',
                        'beats_key',
                        'beats_ca',
                        'beats_cert']
        if self._any_empty(logging_vars):
            for l in logging_vars:
                self.params[l] = ''
        else:
            self.enable_logging = True
        if self._empty_param('session_db_url'):
            self.params[
                'session_db_url'] = 'sqlite:////home/jupyter/jupyterhub.sqlite'
        if self._empty_param('tls_dhparam'):
            self._check_executables(["openssl"])
            if self._empty_param('dhparam_bits'):
                self.params['dhparam_bits'] = 2048

    def _check_sourcedir(self):
        """Look for the deployment files elsewhere in the repository we
        presumably checked this deployment module out from.
        """
        topdir = os.path.realpath(
            os.path.join(ME, "..", "..", "..", ".."))
        for c in self.components:
            cp = os.path.join(topdir, c)
            if not os.path.isdir(cp):
                raise RuntimeError("Directory for component '%s' not " +
                                   "found at %s." % (c, cp))
        self.srcdir = topdir

    def _copy_deployment_files(self):
        """Copy all the kubernetes files to set up a template environment.
        """
        self._check_sourcedir()
        d = self.directory
        t = self.srcdir
        os.mkdir(os.path.join(d, "deployment"))
        for c in self.components:
            shutil.copytree(os.path.join(t, c, "kubernetes"),
                            os.path.join(d, "deployment", c))
        self._copy_oauth_provider()

    def _copy_oauth_provider(self):
        configdir = os.path.join(self.srcdir, "jupyterhub", "sample_configs",
                                 self.params['oauth_provider'])
        targetdir = os.path.join(self.directory, "deployment",
                                 "jupyterhub", "config",
                                 "jupyterhub_config.d")
        logging.info("Copying config %s to %s." % (configdir, targetdir))
        shutil.rmtree(targetdir)
        shutil.copytree(configdir, targetdir)

    def _substitute_templates(self):
        """Walk through template files and make substitutions.
        """
        with _wd(os.path.join(self.directory, "deployment")):
            self._generate_dhparams()
            self._generate_crypto_key()
            matches = {}
            for c in self.components:
                matches[c] = []
                for root, dirnames, filenames in os.walk(c):
                    for fn in fnmatch.filter(filenames, '*.template.yml'):
                        matches[c].append(os.path.join(root, fn))
            for c in self.components:
                templates = matches[c]
                for t in templates:
                    self._substitute_file(t)

    def _generate_crypto_key(self):
        """Get a pair of keys to make rotation easier.
        """
        ck = os.urandom(16).hex() + ";" + os.urandom(16).hex()
        self.params['crypto_key'] = ck

    def _logcmd(self, cmd):
        """Convenience function to display actual subprocess command run.
        """
        cmdstr = " ".join(cmd)
        logging.info("About to run '%s'" % cmdstr)

    def _generate_dhparams(self):
        """If we don't have a param file, make one.  If we do, read it.
        """
        if self._empty_param('tls_dhparam'):
            bits = self.params['dhparam_bits']
            with _wd(self.directory):
                ossl = self.executables["openssl"]
                cmd = [ossl, "dhparam", str(bits)]
                rc = self._run(cmd, capture=True)
                dhp = rc.stdout.decode('utf-8')
                self.params["dhparams"] = dhp
        else:
            with open(self.params['tls_dhparam'], "r") as f:
                dhp = f.read()
                self.params["dhparams"] = dhp

    def encode_value(self, key):
        """Cache and return base64 representation of parameter value,
        suitable for kubernetes secrets."""
        if _empty(self.b64_cache, key):
            val = self.params[key]
            if type(val) is str:
                val = val.encode('utf-8')
            self.b64_cache[key] = base64.b64encode(val).decode('utf-8')
        return self.b64_cache[key]

    def encode_file(self, key):
        """Cache and return base64 representation of file contents at
        path specified in 'key', suitable for kubernetes secrets."""
        path = self.params[key]
        cp = path + "_contents"
        if _empty(self.b64_cache, cp):
            try:
                with open(path, "r") as f:
                    c = f.read()
                    self.params[path] = c
                    b64_c = self.encode_value(path)
                    self.b64_cache[cp] = b64_c
            except IOError:
                self.b64_cache[cp] = ''
        return self.b64_cache[cp]

    def _substitute_file(self, templatefile):
        """Write a non-template version with variables substituted.
        """
        destfile = templatefile[:-13] + ".yml"
        with open(templatefile, 'r') as rf:
            templatetext = rf.read()
            tpl = Template(templatetext)
            out = self._substitute(tpl)
            with open(destfile, 'w') as wf:
                wf.write(out)
        logging.info("Substituted %s -> %s." % (templatefile, destfile))
        os.remove(templatefile)

    def _substitute(self, tpl):
        """Use jinja2 to substitute all the deployment values, although only
        a few will be present in any particular input file.
        """
        p = self.params
        # We do not yet know NFS_SERVER_IP_ADDRESS so leave it a template.
        return tpl.render(CLUSTERNAME=p['kubernetes_cluster_name'],
                          OAUTH_CLIENT_ID=self.encode_value(
                              'oauth_client_id'),
                          OAUTH_SECRET=self.encode_value(
                              'oauth_secret'),
                          OAUTH_CALLBACK_URL=self.encode_value(
                              'oauth_callback_url'),
                          GITHUB_ORGANIZATION_WHITELIST=self.encode_value(
                              'github_organization_whitelist'),
                          CILOGON_GROUP_WHITELIST=self.encode_value(
                              'cilogon_group_whitelist'),
                          SESSION_DB_URL=self.encode_value(
                              'session_db_url'),
                          JUPYTERHUB_CRYPTO_KEY=self.encode_value(
                              'crypto_key'),
                          CLUSTER_IDENTIFIER=p[
                              'kubernetes_cluster_namespace'],
                          SHARED_VOLUME_SIZE=p[
                              'nfs_volume_size'],
                          PHYSICAL_SHARED_VOLUME_SIZE=p[
                              'volume_size'],
                          ROOT_CHAIN_PEM=self.encode_file('tls_root_chain'),
                          DHPARAM_PEM=self.encode_value("dhparams"),
                          TLS_CRT=self.encode_file('tls_cert'),
                          TLS_KEY=self.encode_file('tls_key'),
                          HOSTNAME=p['hostname'],
                          FIREFLY_ADMIN_PASSWORD=self.encode_value(
                              'firefly_admin_password'),
                          CA_CERTIFICATE=self.encode_file('beats_ca'),
                          BEATS_CERTIFICATE=self.encode_file('beats_cert'),
                          BEATS_KEY=self.encode_file('beats_key'),
                          SHIPPER_NAME=p['log_shipper_name'],
                          RABBITMQ_PAN_PASSWORD=self.encode_value(
                              'rabbitmq_pan_password'),
                          RABBITMQ_TARGET_HOST=p['rabbitmq_target_host'],
                          RABBITMQ_TARGET_VHOST=p['rabbitmq_target_vhost'],
                          DEBUG=p['debug'],
                          PREPULLER_IMAGE_LIST=p['prepuller_image_list'],
                          PREPULLER_NO_SCAN=p['prepuller_no_scan'],
                          PREPULLER_REPO=p['prepuller_repo'],
                          PREPULLER_OWNER=p['prepuller_owner'],
                          PREPULLER_IMAGE_NAME=p['prepuller_image_name'],
                          PREPULLER_DAILIES=p['prepuller_dailies'],
                          PREPULLER_WEEKLIES=p['prepuller_weeklies'],
                          PREPULLER_RELEASES=p['prepuller_releases'],
                          PREPULLER_PORT=p['prepuller_port'],
                          PREPULLER_SORT_FIELD=p['prepuller_sort_field'],
                          PREPULLER_COMMAND=p['prepuller_command'],
                          PREPULLER_NAMESPACE=p['prepuller_namespace'],
                          LAB_SELECTOR_TITLE=p['lab_selector_title'],
                          LAB_IDLE_TIMEOUT=p['lab_idle_timeout'],
                          LAB_MEM_LIMIT=p['lab_mem_limit'],
                          LAB_CPU_LIMIT=p['lab_cpu_limit'],
                          LAB_MEM_GUARANTEE=p['lab_mem_guarantee'],
                          LAB_CPU_GUARANTEE=p['lab_cpu_guarantee'],
                          NFS_SERVER_IP_ADDRESS='{{NFS_SERVER_IP_ADDRESS}}',
                          )

    def _rename_fileserver_template(self):
        """We did not finish substituting the fileserver, because
        we need the service address.
        """
        directory = os.path.join(self.directory, "deployment",
                                 "fileserver")
        fnbase = "jld-fileserver-pv"
        src = os.path.join(directory, fnbase + ".yml")
        tgt = os.path.join(directory, fnbase + ".template.yml")
        os.rename(src, tgt)

    def _save_deployment_yml(self):
        """Either save the input file we used, or synthesize one from our
        params.
        """
        tfmt = '%Y-%m-%d-%H-%M-%S-%f-UTC'
        datestr = datetime.datetime.utcnow().strftime(tfmt)
        outf = os.path.join(self.directory, "deploy.%s.yml" % datestr)
        # Use input file if we have it
        if self.yamlfile:
            shutil.copy2(self.yamlfile, outf)
        else:
            ymlstr = "# JupyterLab Demo deployment file\n"
            ymlstr += "# Created at %s\n" % datestr
            cleancopy = self._clean_param_copy()
            ymlstr += yaml.dump(cleancopy, default_flow_style=False)
            with open(outf, "w") as f:
                f.write(ymlstr)

    def _clean_param_copy(self):
        """By the time we deploy, we have a bunch of calculated params.
        Get rid of those so we have a clean input file for the next deployment.
        """
        cleancopy = {}
        pathvars = ['tls_cert', 'tls_key', 'tls_root_chain',
                    'beats_cert', 'beats_key', 'beats_ca']
        fullpathvars = set()
        ignore = ['oauth_callback_url', 'crypto_key', 'dhparams',
                  'nfs_volume_size', 'volume_size']
        for p in pathvars:
            v = self.params.get(p)
            if v:
                fullpathvars.add(v)
        ignore += fullpathvars
        for k, v in self.params.items():
            if not v:
                continue
            if k in ignore:
                continue
            cleancopy[k] = v
        return cleancopy

    def _create_resources(self):
        with self.kubecontext():
            self._create_gke_cluster()
            if self.enable_logging:
                self._create_logging_components()
            if _empty(self.params, "external_fileserver_ip"):
                self._create_fileserver()
                self._create_fs_keepalive()
            else:
                ip = self.params['external_fileserver_ip']
                ns = self.params['kubernetes_cluster_namespace']
                self._substitute_fileserver_ip(ip, ns)
            if self.enable_prepuller:
                self._create_prepuller()
            self._create_jupyterhub()
            self._create_nginx()
            self._create_dns_record()

    def _create_gke_cluster(self):
        """Create cluster and namespace if required.
        """
        mtype = self.params['gke_machine_type']
        nodes = self.params['gke_node_count']
        dsize = self.params['gke_local_volume_size_gigabytes']
        name = self.params['kubernetes_cluster_name']
        namespace = self.params['kubernetes_cluster_namespace']
        if not self.existing_cluster:
            self._run_gcloud(["container", "clusters", "create", name,
                              "--num-nodes=%d" % nodes,
                              "--machine-type=%s" % mtype,
                              "--disk-size=%s" % dsize
                              ])
            self._run_gcloud(["container", "clusters", "get-credentials",
                              name])
        self._switch_to_context(name)
        if namespace != "default" and not self.existing_namespace:
            # This sometimes fails immediately after cluster creation,
            #  so run it under _waitfor()
            self._waitfor(self._create_namespace, delay=1, tries=15)

    def _create_namespace(self):
        rc = self._run(["kubectl", "create", "namespace",
                        self.params['kubernetes_cluster_namespace']],
                       check=False)
        if rc.returncode == 0:
            return True
        return False

    def _destroy_gke_disks(self):
        """Destroy disks."""
        for disk in self.disklist:
            logging.info("Destroying disk '%s'." % disk)
            removable = self._check_disk_removability(disk)
            if removable:
                self._run_gcloud(["compute", "disks", "delete", disk, "-q"],
                                 check=False)
            else:
                logging.warn("Disk '%s' is not removable." % disk)

    def _check_disk_removability(self, disk):
        if not disk:
            logging.warn("No active disk to check removability.")
            return False
        self._activedisk = disk
        try:
            self._waitfor(self._disk_released)
        except RuntimeError as e:
            logging.error(str(e))
            return False
        return True

    def _disk_released(self):
        disk = self._activedisk
        rc = self._run_gcloud(
            ["compute", "disks", "describe", disk, "-q"],
            capture=True, check=False)
        if rc.returncode:
            logging.warn("Disk '%s' indescribable.  Assuming removable.")
            return True
        struct = yaml.load(rc.stdout.decode('utf-8'))
        if "users" in struct:
            ulist = struct["users"]
            if ulist and len(ulist) > 0:
                user = ulist[0].split('/')[-1]
                logging.info("Disk '%s' in use by '%s'." % (disk, user))
                logging.info("Attempting to detach it.")
                self._run_gcloud(["compute", "instances", "detach-disk", user,
                                  "--disk=%s" % disk], check=False)
                return False
        return True

    def _destroy_gke_cluster(self):
        """Destroy cluster and namespace if required.
        """
        name = self.params['kubernetes_cluster_name']
        namespace = self.params['kubernetes_cluster_namespace']
        if namespace != "default" and not self.existing_namespace:
            rc = self._run(
                ["kubectl", "config", "current-context"], capture=True)
            if rc.stdout:
                context = rc.stdout.decode('utf-8').strip()
                self._run(["kubectl", "config", "set-context", context,
                           "--namespace", "default"])
            # If we are destroying the cluster, we don't really care
            #  whether this succeeds.
            self._run(["kubectl", "delete", "namespace", namespace],
                      check=self.existing_cluster)
        if not self.existing_cluster:
            self._run_gcloud(["-q", "container", "clusters", "delete", name])

    def _create_logging_components(self):
        logging.info("Creating logging components.")
        for c in [os.path.join("logstashrmq", "logstashrmq-secrets.yml"),
                  os.path.join("logstashrmq", "logstashrmq-service.yml"),
                  os.path.join("logstashrmq", "logstashrmq-deployment.yml"),
                  os.path.join("filebeat", "filebeat-secrets.yml"),
                  os.path.join("filebeat", "filebeat-daemonset.yml")]:
            self._run_kubectl_create(os.path.join(
                self.directory, "deployment", c))

    def _destroy_logging_components(self):
        logging.info("Destroying logging components.")
        for c in [["daemonset", "filebeat"],
                  ["secret", "filebeat"],
                  ["deployment", "logstash"],
                  ["service", "logstashrmq"],
                  ["secret", "logstashrmq"]]:
            self._run_kubectl_delete(c)

    def _create_fileserver(self):
        logging.info("Creating fileserver.")
        directory = os.path.join(self.directory, "deployment", "fileserver")
        for c in ["jld-fileserver-storageclass.yml",
                  "jld-fileserver-physpvc.yml",
                  "jld-fileserver-service.yml",
                  "jld-fileserver-deployment.yml"]:
            self._run_kubectl_create(os.path.join(directory, c))
        ip = self._waitfor(self._get_fileserver_ip)
        ns = self.params["kubernetes_cluster_namespace"]
        self._substitute_fileserver_ip(ip, ns)
        for c in ["jld-fileserver-pv-%s.yml" % ns,
                  "jld-fileserver-pvc.yml"]:
            self._run_kubectl_create(os.path.join(directory, c))

    def _substitute_fileserver_ip(self, ip, ns):
        """Once we have the (internal) IP of the fileserver service, we
        can substitute it into the deployment template, but that requires the
        service to have been created first.
        """
        directory = os.path.join(self.directory, "deployment", "fileserver")
        with open(os.path.join(directory,
                               "jld-fileserver-pv.template.yml"), "r") as fr:
            tmpl = Template(fr.read())
            out = tmpl.render(NFS_SERVER_IP_ADDRESS=ip)
            with open(os.path.join(directory,
                                   "jld-fileserver-pv-%s.yml" % ns),
                      "w") as fw:
                fw.write(out)

    def _waitfor(self, callback, delay=10, tries=10):
        """Convenience method to loop-and-delay until the callback function
        returns something truthy.
        """
        i = 0
        while True:
            i = i + 1
            rc = callback()
            if rc:
                return rc
            logging.info("Waiting %d seconds [%d/%d]." % (delay, i, tries))
            time.sleep(delay)
            if i == tries:
                raise RuntimeError(
                    "Callback did not succeed after %d %ds iterations" %
                    (tries, delay))

    def _get_fileserver_ip(self):
        """Get IP of fileserver service from YAML output.
        """
        rc = self._run(["kubectl", "get", "svc", "jld-fileserver",
                        "--namespace=%s" %
                        self.params['kubernetes_cluster_namespace'],
                        "-o", "yaml"],
                       check=False,
                       capture=True)
        if rc.stdout:
            struct = yaml.load(rc.stdout.decode('utf-8'))
            if not _empty(struct, "spec"):
                return struct["spec"]["clusterIP"]
        return None

    def _get_external_ip(self):
        """Get external IP of nginx service from YAML output.
        """
        rc = self._run(["kubectl", "get", "svc", "jld-nginx",
                        "--namespace=%s" %
                        self.params['kubernetes_cluster_namespace'],
                        "-o", "yaml"],
                       check=False,
                       capture=True)
        if rc.stdout:
            struct = yaml.load(rc.stdout.decode('utf-8'))
            if not _empty(struct, "status"):
                st = struct["status"]
                if not _empty(st, "loadBalancer"):
                    lb = st["loadBalancer"]
                    if not _empty(lb, "ingress"):
                        ng = lb["ingress"]
                        return ng[0]["ip"]
        return None

    def _get_pods_for_name(self, depname):
        """Determine the pod names for a given deployment.
        """
        logging.info("Getting pod names for '%s'." % depname)
        retval = []
        rc = self._run(["kubectl", "get", "pods", "-o", "yaml"], capture=True)
        struct = yaml.load(rc.stdout.decode('utf-8'))
        for pod in struct["items"]:
            name = pod["metadata"]["name"]
            if name.startswith(depname):
                retval.append(name)
        return retval

    def _get_pv_and_disk_from_pvc(self, pvc):
        """Given a PVC name, get the PV and disk it's bound to.
        """
        logging.info("Getting PV and disk names for PVC '%s'." % pvc)
        pv = None
        disk = None
        rc = self._run(["kubectl", "get", "pvc", "-o", "yaml", pvc],
                       capture=True, check=False)
        if rc.returncode != 0:
            return pv
        struct = yaml.load(rc.stdout.decode('utf-8'))
        if "spec" in struct and "volumeName" in struct["spec"]:
            pv = struct["spec"]["volumeName"]
        if pv:
            logging.info("Getting disk name for PV '%s'." % pv)
            rc = self._run(["kubectl", "get", "pv", "-o", "yaml", pv],
                           capture=True, check=False)
            if rc.returncode != 0:
                return pv
            struct = yaml.load(rc.stdout.decode('utf-8'))
            if ("spec" in struct and "gcePersistentDisk" in struct["spec"]
                    and "pdName" in struct["spec"]["gcePersistentDisk"]):
                disk = struct["spec"]["gcePersistentDisk"]["pdName"]
                self.disklist.append(disk)
        return pv

    def _destroy_fileserver(self):
        logging.info("Destroying fileserver.")
        ns = self.params["kubernetes_cluster_namespace"]
        pv = self._get_pv_and_disk_from_pvc("jld-fileserver-physpvc")
        items = [["pvc", "jld-fileserver-home"],
                 ["pv", "jld-fileserver-home-%s" % ns],
                 ["service", "jld-fileserver"],
                 ["pvc", "jld-fileserver-physpvc"],
                 ["deployment", "jld-fileserver"],
                 ["storageclass", "fast"]]
        if pv:
            items.append(["pv", pv])
        for c in items:
            self._run_kubectl_delete(c)
        self._destroy_pods_with_callback(self._check_fileserver_gone,
                                         "fileserver")

    def _destroy_pods_with_callback(self, callback, poddesc, tries=60):
        """Wait for pods to exit; if they don't within the specified
        time, either explode or continue, depending on whether we want to
        keep the cluster around.
        """
        logging.info("Waiting for %s pods to exit." % poddesc)
        try:
            self._waitfor(callback=callback, tries=tries)
        except Exception:
            if self.existing_cluster:
                # If we aren't destroying the cluster, then failing to
                #  take down the keepalive pod means we're going to fail.
                # If we are, the cluster teardown means we don't actually
                #  care a lot whether or not the individual deployment
                #  destructions work.
                raise
            logging.warn("All %s pods did not exit.  Continuing." % poddesc)
            return
        logging.warn("All %s pods exited." % poddesc)

    def _create_fs_keepalive(self):
        logging.info("Creating fs-keepalive")
        self._run_kubectl_create(os.path.join(
            self.directory,
            "deployment",
            "fs-keepalive",
            "jld-keepalive-deployment.yml"
        ))

    def _destroy_fs_keepalive(self):
        logging.info("Destroying fs-keepalive")
        self._run_kubectl_delete(["deployment", "jld-keepalive"])
        self._destroy_pods_with_callback(self._check_keepalive_gone,
                                         "keepalive")

    def _check_keepalive_gone(self):
        return self._check_pods_gone("jld-keepalive")

    def _check_fileserver_gone(self):
        return self._check_pods_gone("jld-fileserver")

    def _check_pods_gone(self, name):
        """Used as a callback for _waitfor(); return True only when all
        the pods for a deployment are gone.
        """
        pods = self._get_pods_for_name(name)
        if pods:
            return None
        return True

    def _create_prepuller(self):
        logging.info("Creating prepuller")
        self._run_kubectl_create(os.path.join(
            self.directory,
            "deployment",
            "prepuller",
            "prepuller-cronjob.yml"
        ))

    def _destroy_prepuller(self):
        logging.info("Destroying prepuller")
        self._run_kubectl_delete(["cronjob", "prepuller"])

    def _create_jupyterhub(self):
        logging.info("Creating JupyterHub")
        directory = os.path.join(self.directory, "deployment", "jupyterhub")
        for c in ["jld-hub-service.yml", "jld-hub-physpvc.yml",
                  "jld-hub-secrets.yml"]:
            self._run_kubectl_create(os.path.join(directory, c))
        cfdir = os.path.join(directory, "config")
        cfnm = "jupyterhub_config"
        self._run(['kubectl', 'create', 'configmap', 'jld-hub-config',
                   "--from-file=%s" % os.path.join(cfdir, "%s.py" % cfnm),
                   "--from-file=%s" % os.path.join(cfdir, "%s.d" % cfnm)])
        self._run_kubectl_create(os.path.join(
            directory, "jld-hub-deployment.yml"))

    def _destroy_jupyterhub(self):
        logging.info("Destroying JupyterHub")
        pv = self._get_pv_and_disk_from_pvc("jld-hub-physpvc")
        items = [["deployment", "jld-hub"],
                 ["configmap", "jld-hub-config"],
                 ["secret", "jld-hub"],
                 ["pvc", "jld-hub-physpvc"],
                 ["svc", "jld-hub"]]
        if pv:
            items.append(["pv", pv])
        for c in items:
            self._run_kubectl_delete(c)

    def _create_nginx(self):
        logging.info("Creating Nginx")
        directory = os.path.join(self.directory, "deployment", "nginx")
        for c in ["tls-secrets.yml",
                  "nginx-service.yml",
                  "nginx-deployment.yml"]:
            self._run_kubectl_create(os.path.join(directory, c))

    def _destroy_nginx(self):
        logging.info("Destroying Nginx")
        for c in [["deployment", "jld-nginx"],
                  ["svc", "jld-nginx"],
                  ["secret", "tls"]]:
            self._run_kubectl_delete(c)

    def _create_dns_record(self):
        logging.info("Creating DNS record")
        self._change_dns_record("create")

    def _change_dns_record(self, action):
        """Create changeset record and then submit it to AWS.
        """
        zoneid = self.params["zoneid"]
        record = {
            "Comment": "JupyterLab Demo %s/%s" % (
                self.params['kubernetes_cluster_name'],
                self.params['kubernetes_cluster_namespace'],
            ),
            "Changes": []
        }
        if action == "create":
            record["Changes"] = self._generate_upsert_dns()
        elif action == "delete":
            record["Changes"] = self._generate_delete_dns()
        else:
            raise RuntimeError("DNS action must be 'create' or 'delete'")
        with tempfile.TemporaryDirectory() as d:
            # We don't care about keeping the changeset request around
            changeset = os.path.join(d, "rr-changeset.txt")
            with open(changeset, "w") as f:
                json.dump(record, f)
            self._run(["aws", "route53", "change-resource-record-sets",
                       "--hosted-zone-id", zoneid, "--change-batch",
                       "file://%s" % changeset, "--output", "json"])

    def _generate_upsert_dns(self):
        """Create changeset for DNS create-or-update request.
        """
        ip = self._waitfor(callback=self._get_external_ip, tries=30)
        return [
            {
                "Action": "UPSERT",
                "ResourceRecordSet": {
                    "Name": self.params["hostname"],
                    "Type": "A",
                    "TTL": 60,
                    "ResourceRecords": [
                        {
                            "Value": ip
                        }
                    ]
                }
            }
        ]

    def _generate_delete_dns(self):
        """Create changeset for DNS deletion request.
        """
        host = self.params["hostname"]
        answer = dns.resolver.query(host, 'A')
        response = answer.rrset.to_text().split()
        ttl = int(response[1])
        ip = response[4]
        return [
            {
                "Action": "DELETE",
                "ResourceRecordSet": {
                    "Name": host + ".",
                    "Type": "A",
                    "TTL": ttl,
                    "ResourceRecords": [
                        {
                            "Value": ip
                        }
                    ]
                }
            }
        ]

    def _destroy_dns_record(self):
        logging.info("Destroying DNS record")
        try:
            self._change_dns_record("delete")
        except Exception as e:
            logging.warn("Failed to destroy DNS record: %s" % str(e))

    def _destroy_resources(self):
        with self.kubecontext():
            self._switch_to_context(self.params["kubernetes_cluster_name"])
            self._destroy_dns_record()
            self._destroy_nginx()
            self._destroy_jupyterhub()
            self._destroy_prepuller()
            self._destroy_fs_keepalive()
            self._destroy_fileserver()
            self._destroy_logging_components()
            self._destroy_gke_cluster()
            self._destroy_gke_disks()

    def _run_gcloud(self, args, check=True, capture=False):
        """Convenience method for running gcloud in the right zone.
        """
        newargs = (["gcloud"] +
                   args +
                   ["--zone=%s" % self.params["gke_zone"]] +
                   ["--format=yaml"])
        return self._run(newargs, check=check, capture=capture)

    def _run_kubectl_create(self, filename):
        """Convenience method to create a kubernetes resource from a file.
        """
        self._run(['kubectl', 'create', '-f', filename, "--namespace=%s" %
                   self.params["kubernetes_cluster_namespace"]])

    def _run_kubectl_delete(self, component):
        """Convenience method to delete a kubernetes resource.
        """
        self._run(['kubectl', 'delete'] + component +
                  ["--namespace=%s" % (
                      self.params["kubernetes_cluster_namespace"])],
                  check=False)

    def _switch_to_context(self, name):
        """Save current context, if set, and change to a new one.
        """
        context = None
        rc = self._run(["kubectl", "config", "get-contexts"], capture=True)
        if rc.stdout:
            lines = rc.stdout.decode('utf-8').split('\n')
            for l in lines:
                w = l.split()
                t_context = w[0]
                if t_context == '*':
                    t_context = w[1]
                if t_context.endswith(name):
                    context = t_context
                    break
        if not context:
            raise RuntimeError(
                "Could not find context for cluster '%s'" % name)
        self._run(["kubectl", "config", "use-context", context])
        self._run(["kubectl", "config", "set-context", context,
                   "--namespace", self.params['kubernetes_cluster_namespace']])

    def _create_deployment(self):
        """Use params to determine whether to deploy or just configure, and
        whether to keep the directory around or not.
        """
        d = self.directory
        hn = self.params['hostname']
        if not d:
            if self.temporary:
                with tempfile.TemporaryDirectory() as d:
                    self.directory = d
                    self._generate_config()
                    self._create_resources()
                self.directory = None
                return
            else:
                d = os.path.join(os.getcwd(), "configurations", hn)
                self.directory = d
        d = self.directory
        if not os.path.isdir(d):
            os.makedirs(d)
        if not os.path.isdir(os.path.join(d, "deployment")):
            self._generate_config()
            cfgtext = "Configuration for %s generated in %s." % (hn, d)
            logging.info(cfgtext)
        if self.config_only:
            return
        self._create_resources()
        logging.info("Deployment of %s complete." % hn)

    def _generate_config(self):
        """Generate deployment configuration and write it out.
        """
        with _wd(self.directory):
            self._check_sourcedir()
            self._copy_deployment_files()
            self._substitute_templates()
            self._rename_fileserver_template()
            self._save_deployment_yml()

    def deploy(self):
        """Deploy JupyterLab Demo cluster.
        """
        if not self.yamlfile and not self.params:
            errstr = "YAML file or parameter set required."
            raise ValueError(errstr)
        self._set_params()
        self._validate_deployment_params()
        self._normalize_params()
        self._create_deployment()
        logging.info("Finished.")

    def undeploy(self):
        """Remove JupyterLab Demo cluster.
        """
        self._set_params()
        self.directory = os.getenv("TMPDIR") or "/tmp"
        self._get_cluster_info()
        self._destroy_resources()
        hn = self.params['hostname']
        logging.info("Removal of %s complete." % hn)


def get_cli_options():
    """Parse command-line arguments."""
    desc = "Deploy or destroy the JupyterLab Demo environment. "
    desc += ("Parameters may be set from\neither the YAML file specified " +
             "with the -f option, or from an environment\nvariable.  The " +
             "form of the environment variable is JLD_ prepended to the\n" +
             "parameter name.\n\n")
    desc += ("The 'hostname' parameter is always required, for both " +
             "deployment and\ndestruction.  It must be the FQDN of the " +
             "external endpoint.\n\n")
    desc += ("Although the 'kubernetes_cluster_name' parameter must be " +
             "known, it will\ndefault to the hostname with dots replaced " +
             "by dashes.\n\n")
    desc += ("The 'oauth_provider' must be 'github' or 'cilogon'.  It " +
             "defaults to 'github'.\n\n")
    desc += ("For deployment, the following set of parameters is " +
             "required:\n%s.\n\n" % REQUIRED_DEPLOYMENT_PARAMETER_NAMES)
    desc += ("The TLS information can be set by defining " +
             "JLD_CERTIFICATE_DIRECTORY and then\nputting 'cert.pem', " +
             "'key.pem', and 'chain.pem' in it.  If you put\n" +
             "'dhparam.pem' there as well, it will be used rather than " +
             "generated.\nAdditionally, if you are using the " +
             "logging components, if you put\n'beats_cert.pem', " +
             "'beats_ca.pem', and 'beats_key.pem' in the same directory,\n" +
             "they will be used as well.\n\n")
    desc += ("The 'allowed_groups' parameter is a list in " +
             "the YAML file; as the\nenvironment variable JLD_ALLOWED_GROUPS" +
             " it must be a comma-separated\n" +
             "list of GitHub organization names or CILogon/NCSA " +
             "group names.\n\n")
    desc += ("The 'cilogon_group_whitelist' or " +
             "'github_organization_whitelist' parameters\n" +
             "may be used directly in place of 'allowed-groups'.\n\n")
    desc += ("All deployment parameters may be set from the environment, " +
             "not just\nrequired ones. The complete set of recognized " +
             "parameters is:\n%s.\n\n" % PARAMETER_NAMES)
    desc += ("Therefore the set of allowable environment variables is:\n" +
             "%s.\n\n" % ["JLD_" + x.upper() for x in PARAMETER_NAMES])
    hf = argparse.RawDescriptionHelpFormatter
    pr = argparse.ArgumentParser(description=desc,
                                 formatter_class=hf)
    pr.add_argument("-c", "--create-config", "--create-configuration",
                    help=("Create configuration only.  Do not deploy." +
                          " Incompatible with -t."), action='store_true')
    pr.add_argument("-d", "--directory",
                    help=("Use specified directory.  If " +
                          "directory already contains configuration " +
                          "files, use them instead of resubstituting. " +
                          "Defaults to " +
                          "./configurations/[FQDN-of-deployment]. " +
                          "Incompatible with -t."),
                    default=None)
    pr.add_argument("-f", "--file", "--input-file",
                    help=("YAML file specifying demo parameters.  " +
                          "Respected for undeployment as well.  If " +
                          "present, used instead of environment or " +
                          "prompt."),
                    default=None)
    pr.add_argument("-t", "--temporary",
                    help="Write config to temporary directory and " +
                    "remove after deployment.  Incompatible with -d.",
                    action="store_true")
    pr.add_argument("-u", "--undeploy", "--destroy", "--remove",
                    help="Undeploy JupyterLab Demo cluster.",
                    action='store_true')
    pr.add_argument("--disable-prepuller", "--no-prepuller",
                    help="Do not deploy prepuller",
                    action='store_true')
    pr.add_argument(
        "--existing-cluster", help=("Do not create/destroy cluster.  " +
                                    "Respected for undeployment as well."),
        action='store_true')
    pr.add_argument(
        "--existing-namespace", help=("Do not create/destroy namespace.  " +
                                      "Respected for undeployment as well." +
                                      "  Requires --existing-cluster."),
        action='store_true')
    result = pr.parse_args()
    dtype = "deploy"
    if "undeploy" in result and result.undeploy:
        dtype = "undeploy"
    if "file" not in result or not result.file:
        result.params = get_options_from_environment()
        complete = True
        req_ps = REQUIRED_PARAMETER_NAMES
        if dtype == "deploy":
            req_ps = REQUIRED_DEPLOYMENT_PARAMETER_NAMES
        for n in req_ps:
            if _empty(result, n):
                complete = False
                break
        if not complete:
            result.params = get_options_from_user(dtype=dtype,
                                                  params=result.params)
        result.params = _canonicalize_result_params(result.params)
    return result


def get_options_from_environment(dtype="deploy"):
    """Use environment variables to set deployment/removal parameters
    when there is no YAML file.
    """
    retval = {}
    for n in PARAMETER_NAMES:
        e = os.getenv(ENVIRONMENT_NAMESPACE + n.upper())
        if e:
            retval[n] = e
    if _empty(retval, "tls_cert"):
        e = os.getenv(ENVIRONMENT_NAMESPACE + "CERTIFICATE_DIRECTORY")
        if e:
            do_beats = _empty(retval, "beats_cert")
            retval.update(_set_certs_from_dir(e, beats=do_beats))
    return retval


def _set_certs_from_dir(d, beats=False):
    """The common use case will be to specify a single directory that all
    your TLS certificates live in.  This is easier than specifying each
    file individually.
    """
    retval = {}
    retval["tls_cert"] = os.path.join(d, "cert.pem")
    retval["tls_key"] = os.path.join(d, "key.pem")
    retval["tls_root_chain"] = os.path.join(d, "chain.pem")
    dhfile = os.path.join(d, "dhparam.pem")
    if os.path.exists(dhfile):
        retval["tls_dhparam"] = dhfile
    if beats:
        beats_cert = os.path.join(d, "beats_cert.pem")
        if os.path.exists(beats_cert):
            retval["beats_cert"] = beats_cert
            retval["beats_ca"] = os.path.join(d, "beats_ca.pem")
            retval["beats_key"] = os.path.join(d, "beats_key.pem")
    return retval


def _canonicalize_result_params(params):
    """Manage environment (string) to actual data structure (int or list)
    conversion.
    """

    wlname = "github_organization_whitelist"
    if params["oauth_provider"] == "cilogon":
        wlname = "cilogon_group_whitelist"
    if _empty(params, wlname):
        if not _empty(params, "allowed_groups"):
            params[wlname] = params["allowed_groups"]
    if not _empty(params, wlname):
        owl = params[wlname]
        if type(owl) is str:
            params[wlname] = owl.split(',')
    for intval in ["gke_node_count", "volume_size_gigabytes",
                   "gke_default_volume_size_gigabytes"]:
        if not _empty(params, intval):
            params[intval] = int(params[intval])
    return params


def get_options_from_user(dtype="deploy", params={}):
    """If we do not have a YAML file, and we are missing environment variables
    for required configuration, then ask the user for them on stdin.

    Anything not required is defaulted, so, for instance, if you want to set
    the cluster namespace, you need to set JLD_KUBERNETES_CLUSTER_NAMESPACE in
    the environment.
    """
    prompt = {"kubernetes_cluster_name": ["Kubernetes Cluster Name", None],
              "hostname": ["JupyterLab Demo hostname (FQDN)", None],
              "oauth_client_id": ["OAuth Client ID", None],
              "oauth_secret": ["OAuth Secret", None],
              "oauth_provider": ["OAuth provider", "github"],
              "allowed_groups": ["Allowed Groups", None],
              }
    params.update(_get_values_from_prompt(params, ['hostname'], prompt))
    if _empty(params, "kubernetes_cluster_name"):
        hname = params['hostname']
        cname = hname.translate({ord('.'): '-'})
        params["kubernetes_cluster_name"] = cname
        logging.warn("Using derived cluster name '%s'." % cname)
    if dtype == "deploy":
        params.update(_get_values_from_prompt(
            params, ['oauth_provider'], prompt))
        if _empty(params, "tls_cert"):
            line = ""
            while not line:
                line = input("TLS Certificate Directory: ")
            params.update(_set_certs_from_dir(line))
        params.update(_get_values_from_prompt(
            params, REQUIRED_DEPLOYMENT_PARAMETER_NAMES, prompt))
        if params["oauth_provider"] == "cilogon":
            params["cilogon_group_whitelist"] = params["allowed_groups"]
        else:
            params["github_organization_whitelist"] = params["allowed_groups"]
    else:
        # Provider doesn't matter for teardown.
        if _empty(params, "oauth_provider"):
            params["oauth_provider"] = "github"
    return params


def _get_values_from_prompt(params, namelist, prompts={}):
    """Convenience function to read from stdin.
    """
    for n in namelist:
        if _empty(params, n):
            line = ""
            pr, dfl = prompts.get(n) or [n, None]
            while not line:
                prpt = pr
                if dfl:
                    prpt += " [" + dfl + "]"
                prpt += ": "
                line = input(prpt)
                if not line and dfl:
                    line = dfl
            params[n] = line
    return params


@contextmanager
def _wd(newdir):
    """Save and restore working directory.
    """
    cwd = os.getcwd()
    os.chdir(newdir)
    yield
    os.chdir(cwd)


def _empty(input_dict, k):
    """Empty unless key exists and its value is truthy.
    """
    if k in input_dict and input_dict[k]:
        return False
    return True


def _which(program):
    """Resolve a program that's in $PATH:
    https://stackoverflow.com/questions/377017
    """
    def is_exe(fpath):
        """Test existence and executability.
        """
        return os.path.isfile(fpath) and os.access(fpath, os.X_OK)
    fpath, fname = os.path.split(program)
    if fpath:
        if is_exe(program):
            return program
    else:
        ospath = os.getenv("PATH")
        for path in ospath.split(os.pathsep):
            exe_file = os.path.join(path, program)
            if is_exe(exe_file):
                return exe_file
    return None


def standalone_deploy(options):
    """Entrypoint for running deployment as an executable.
    """
    d_p = options.disable_prepuller
    y_f = options.file
    e_c = options.existing_cluster
    e_n = options.existing_namespace
    e_d = options.directory
    c_c = options.create_config
    t_t = options.temporary
    p_p = None
    if "params" in options:
        p_p = options.params
    deployment = JupyterLabDeployment(yamlfile=y_f,
                                      disable_prepuller=d_p,
                                      existing_cluster=e_c,
                                      existing_namespace=e_n,
                                      directory=e_d,
                                      config_only=c_c,
                                      params=p_p,
                                      temporary=t_t
                                      )
    deployment.deploy()


def standalone_undeploy(options):
    """Entrypoint for running undeployment as an executable.
    """
    y_f = options.file
    e_c = options.existing_cluster
    e_n = options.existing_namespace
    p_p = None
    if "params" in options:
        p_p = options.params
    deployment = JupyterLabDeployment(yamlfile=y_f,
                                      existing_cluster=e_c,
                                      existing_namespace=e_n,
                                      params=p_p
                                      )
    deployment.undeploy()


def standalone():
    """Entrypoint for running class as an executable.
    """
    logging.basicConfig(format='%(levelname)s %(asctime)s | %(message)s',
                        datefmt='%m/%d/%Y %I:%M:%S %p',
                        level=logging.DEBUG)
    # Not having readline is OK.
    try:
        import readline  # NoQA
    except ImportError:
        logging.warn("No readline library found; no elaborate input editing.")
    options = get_cli_options()
    if options.undeploy:
        standalone_undeploy(options)
    else:
        standalone_deploy(options)


if __name__ == "__main__":
    standalone()
