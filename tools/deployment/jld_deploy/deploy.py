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
    callback that is 'https://fqdn.of.jupyterlab.demo/nb/hub/oauth_callback'.
    ( "/nb/" is configurable, but is the default hub_route value )
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
import random
import semver
import shutil
import string
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
DEFAULT_GKE_MACHINE_TYPE = "n1-standard-4"
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
    "forbidden_groups",
    "github_organization_denylist",
    "cilogon_group_denylist",
    "oauth_provider",
    "tls_dhparam",
    "kubernetes_cluster_namespace",
    "gke_project",
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
    "firefly_replicas",
    "firefly_container_mem_limit",
    "firefly_container_cpu_limit",
    "firefly_max_jvm_size",
    "firefly_uid",
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
    "lab_repo_owner",
    "lab_repo_name",
    "lab_repo_host",
    "lab_image",
    "lab_selector_title",
    "lab_idle_timeout",
    "lab_cpu_limit",
    "lab_mem_limit",
    "lab_cpu_guarantee",
    "lab_mem_guarantee",
    "tiny_cpu_max",
    "mb_per_cpu",
    "lab_size_range",
    "auto_repo_urls",
    "allow_dask_spawn",
    "size_index",
    "hub_route",
    "firefly_route",
    "restrict_lab_nodes",
    "restrict_dask_nodes",
    "debug"]
MTPTS = ["home", "scratch", "project", "datasets", "software"]


class JupyterLabDeployment(object):
    """JupyterLab Deployment object.
    """
    directory = None
    components = ["logstashrmq", "filebeat", "fileserver", "fs-keepalive",
                  "firefly", "prepuller", "jupyterhub", "tls",
                  "nginx-ingress", "landing-page"]
    params = None
    yamlfile = None
    original_context = None
    enable_firefly = False
    enable_prepuller = True
    enable_logging = False
    existing_cluster = False
    existing_namespace = False
    existing_database_instance = False
    existing_database = False
    enable_landing_page = True
    b64_cache = {}
    executables = {}
    srcdir = None
    disklist = []
    _activedisk = None
    _database = None

    def __init__(self, yamlfile=None, params=None, directory=None,
                 disable_prepuller=False, existing_cluster=False,
                 existing_namespace=False, existing_database_instance=False,
                 existing_database=False, config_only=False, temporary=False):
        self.config_only = config_only
        self._check_executables(EXECUTABLES)
        if yamlfile:
            self.yamlfile = os.path.realpath(yamlfile)
        self.existing_cluster = existing_cluster
        self.existing_namespace = existing_namespace
        self.existing_database_instance = existing_database_instance
        self.existing_database = existing_database
        self.temporary = temporary
        self.directory = directory
        if self.directory:
            self.directory = os.path.realpath(self.directory)
            self.temporary = False
        self.params = params
        if disable_prepuller:
            self.enable_prepuller = False

    @contextmanager
    def kubecontext(self):
        """Save and restore original Kubernetes context.
        """
        self._check_authentication()
        savec = ["kubectl", "config", "current-context"]
        self._check_kubectl_version()
        rc = self._run(savec, capture=True, check=False)
        if rc.stdout:
            self.original_context = rc.stdout.decode('utf-8').strip()
        yield
        if self.original_context:
            restorec = ["kubectl", "config",
                        "use-context", self.original_context]
            self._run(restorec, check=False)

    def _check_kubectl_version(self):
        """Make sure we have kubectl 1.10 or later; we need that for the
        landing page configuration to be stored as a binary ConfigMap.

        If we are running configuration-only, no need to do this.
        """
        if self.config_only:
            logging.info("No need to check kubectl version for " +
                         "config-only operation.")
            return
        rc = self._run(["kubectl", "-o", "yaml", "version"], capture=True)
        if rc.stdout:
            result = yaml.safe_load(rc.stdout.decode('utf-8'))
            cv = result["clientVersion"]
            vstr = cv["major"] + "." + cv["minor"] + ".0"
            if semver.match(vstr, "<1.10.0"):
                errstr = "kubectl 1.10 required; %s present" % vstr
                raise RuntimeError(errstr)

    def _get_correct_k8s_version(self):
        """We need the cluster to be at least Kubernetes 1.10 in order
        to have a binary ConfigMap for the landing page.  If the default
        version is not 1.10 or later, use the latest master version that
        exists, which, unless you have a time machine, will always be at
        least 1.10.
        """
        rc = self._run_gcloud(["container", "get-server-config"], capture=True)
        if rc.stdout:
            result = yaml.safe_load(rc.stdout.decode('utf-8'))
            defver = result["defaultClusterVersion"]
            if semver.match(defver, ">=1.10.0"):
                return defver
            return result["validMasterVersions"][0]

    def _check_authentication(self):
        """We also set the AWS zone id from this: if the hostname is not
        in an AWS hosted zone, we want to fail sooner rather than later.
        """
        if self.config_only:
            logging.info("No need to check authetication for config-only " +
                         "operation.")
            return
        logging.info("Checking authentication.")
        cmd = "gcloud info --format yaml".split()
        rc = self._run(cmd, capture=True)
        if rc.returncode == 0:
            gstruct = yaml.safe_load(rc.stdout.decode('utf-8'))
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
                self.params = yaml.safe_load(f)
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
        self.params['gke_region'] = '-'.join(self.params["gke_zone"].
                                             split('-')[:-1])
        if not self._empty_param('gke_project'):
            logging.info("Using gke project '%s'." %
                         self.params["gke_project"])
        else:
            rc = self._run(["gcloud", "config", "get-value", "project",
                            "--format=yaml"], capture=True)
            if rc.stdout:
                result = yaml.safe_load(rc.stdout.decode('utf-8'))
                if not result:
                    raise RuntimeError("gke_project not specified " +
                                       "and no default set.")
                logging.info("Using default gke project '%s'." % result)
                self.params["gke_project"] = result

    def _validate_deployment_params(self):
        """Verify that we have what we need, and get sane defaults for things
        that can be defaulted.
        """
        self._get_cluster_info()
        if self._empty_param('oauth_provider'):
            self.params['oauth_provider'] = OAUTH_DEFAULT_PROVIDER
        if self._empty_param("allowed_groups"):
            if self.params["oauth_provider"] == "cilogon":
                self.params["allowed_groups"] = self.params.get(
                    "cilogon_group_whitelist")
            else:
                self.params["allowed_groups"] = self.params.get(
                    "github_organization_whitelist")
        else:
            if self.params["oauth_provider"] == OAUTH_DEFAULT_PROVIDER:
                if self._empty_param("github_organization_whitelist"):
                    self.params[
                        "github_organization_whitelist"] = self.params.get(
                            "allowed_groups")
            else:
                if self._empty_param("cilogon_group_whitelist"):
                    self.params[
                        "cilogon_group_whitelist"] = self.params.get(
                            "allowed_groups")
        if self._any_empty(REQUIRED_PARAMETER_NAMES):
            raise ValueError("All parameters '%s' must be specified!" %
                             str(REQUIRED_PARAMETER_NAMES))
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
        if self.params['oauth_provider'] != OAUTH_DEFAULT_PROVIDER:
            if self._empty_param('github_organization_whitelist'):
                # Not required if we aren't using GitHub.
                self.params['github_organization_whitelist'] = ["dummy"]
        if self.params['oauth_provider'] != "cilogon":
            if self._empty_param('cilogon_group_whitelist'):
                # Not required if we aren't using CILogon.
                self.params['cilogon_group_whitelist'] = ["dummy"]
        # Some parameters default to empty
        for default_empty in ['debug', 'allow_dask_spawn',
                              'restrict_lab_nodes', 'restrict_dask_nodes']:
            if self._empty_param(default_empty):
                self.params[default_empty] = ''  # Empty is correct
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
        if self._empty_param('lab_repo_owner'):
            self.params['lab_repo_owner'] = self.params['prepuller_owner']
        if self._empty_param('lab_repo_name'):
            self.params['lab_repo_name'] = self.params['prepuller_image_name']
        if self._empty_param('lab_repo_host'):
            self.params['lab_repo_host'] = self.params['prepuller_repo']
        if self._empty_param('lab_image'):
            self.params['lab_image'] = ''
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
        if self._empty_param('tiny_max_cpu'):
            self.params['tiny_max_cpu'] = "0.5"
        if self._empty_param('mb_per_cpu'):
            self.params['mb_per_cpu'] = "2048"
        if self._empty_param('lab_size_range'):
            self.params['lab_size_range'] = "4.0"
        if self._empty_param('hub_route'):
            self.params['hub_route'] = "/nb/"
        if self._empty_param('firefly_route'):
            self.params['firefly_route'] = "/firefly/"
        # Routes must start and end with slash; we know they are not empty.
        for i in ['hub_route', 'firefly_route']:
            if self.params[i][0] != "/":
                self.params[i] = "/" + self.params[i]
            if self.params[i][-1] != "/":
                self.params[i] = self.params[i] + "/"
        if self.params['hub_route'] == '/':
            self.params['enable_landing_page'] = False
        # Sane defaults for Firefly servers
        if self._empty_param('firefly_replicas'):
            self.params['firefly_replicas'] = 1
        if self._empty_param('firefly_container_mem_limit'):
            self.params['firefly_container_mem_limit'] = '4G'
        if self._empty_param('firefly_container_cpu_limit'):
            self.params['firefly_container_cpu_limit'] = '3.0'
        if self._empty_param('firefly_max_jvm_size'):
            self.params['firefly_max_jvm_size'] = '3584M'
        if self._empty_param('firefly_uid'):
            self.params['firefly_uid'] = '91'
        # More defaults
        if self._empty_param('auto_repo_urls'):
            self.params['auto_repo_urls'] = \
                'https://github.com/lsst-sqre/notebook-demo'
        if self._empty_param('size_index'):
            self.params['size_index'] = '1'
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
        self.params['oauth_callback_url'] = ("https://" +
                                             self.params['hostname'] +
                                             self.params['hub_route'] +
                                             "hub/oauth_callback")
        self.params["github_organization_whitelist"] = ','.join(
            self.params["github_organization_whitelist"])
        self.params["cilogon_group_whitelist"] = ','.join(
            self.params["cilogon_group_whitelist"])
        if not self._empty_param("forbidden_groups"):
            oap = self.param["oauth_provider"]
            pnm = "cilogon_group_denylist"
            if oap != "cilogon":
                pnm = "github_organization_denylist"
            self.params[pnm] = self.params["forbidden_groups"]
        if not self._empty_param("github_organization_denylist"):
            self.params["github_organization_denylist"] = ','.join(
                self.params["github_organization_denylist"])
        else:
            self.params["github_organization_denylist"] = ''
        if not self._empty_param("cilogon_group_denylist"):
            self.params["cilogon_group_denylist"] = ','.join(
                self.params["cilogon_group_denylist"])
        else:
            self.params["cilogon_group_denylist"] = ''
        if not self._empty_param("prepuller_image_list"):
            self.params["prepuller_image_list"] = ",".join(
                self.params["prepuller_image_list"])
        now = datetime.datetime.now()
        # First prepuller run in 15 minutes; should give us time to finish
        self.params["prepuller_minute"] = (now.minute + 15) % 60
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
            # cloudsql isn't working correctly yet
            pw = self._generate_random_pw()
            # ns = self.params["kubernetes_cluster_namespace"]
            # url = "mysql://proxyuser:" + pw + "@127.0.0.1:3306/" + ns
            url = "sqlite:////home/jupyter/jupyterhub.sqlite"
            self.params['session_db_url'] = url
            self.params['session_db_pw'] = pw
            # Used to be 'sqlite:////home/jupyter/jupyterhub.sqlite'
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
        d = self.directory
        t = self.srcdir
        os.mkdir(os.path.join(d, "deployment"))
        for c in self.components:
            shutil.copytree(os.path.join(t, c, "kubernetes"),
                            os.path.join(d, "deployment", c))
        self._copy_oauth_provider()

    def _copy_oauth_provider(self):
        """Copy the right set of config files, based on oauth_provider.
        """
        configdir = os.path.join(self.srcdir, "jupyterhub", "sample_configs",
                                 self.params['oauth_provider'])
        target_pdir = os.path.join(self.directory, "deployment",
                                   "jupyterhub", "config")
        os.makedirs(target_pdir, exist_ok=True)
        targetdir = os.path.join(target_pdir, "jupyterhub_config.d")
        logging.info("Copying config %s to %s." % (configdir, targetdir))
        shutil.rmtree(targetdir, ignore_errors=True)
        shutil.copytree(configdir, targetdir)
        jc_py = os.path.join(self.srcdir, "jupyterhub",
                             "jupyterhub_config",
                             "jupyterhub_config.py")
        logging.info("Copying %s to %s" % (jc_py, target_pdir))
        shutil.copyfile(jc_py, os.path.join(target_pdir,
                                            "jupyterhub_config.py"))

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

    def _generate_random_pw(self, len=16):
        """Generate a random string for use as a password.
        """
        charset = string.ascii_letters + string.digits
        return ''.join(random.choice(charset) for x in range(len))

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
        #  Same with DB_IDENTIFIER
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
                          GITHUB_ORGANIZATION_DENYLIST=self.encode_value(
                              'github_organization_denylist'),
                          CILOGON_GROUP_DENYLIST=self.encode_value(
                              'cilogon_group_denylist'),
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
                          PREPULLER_MINUTE=p['prepuller_minute'],
                          LAB_REPO_HOST=p['lab_repo_host'],
                          LAB_REPO_OWNER=p['lab_repo_owner'],
                          LAB_REPO_NAME=p['lab_repo_name'],
                          LAB_IMAGE=p['lab_image'],
                          LAB_SELECTOR_TITLE=p['lab_selector_title'],
                          LAB_IDLE_TIMEOUT=p['lab_idle_timeout'],
                          LAB_MEM_LIMIT=p['lab_mem_limit'],
                          LAB_CPU_LIMIT=p['lab_cpu_limit'],
                          LAB_MEM_GUARANTEE=p['lab_mem_guarantee'],
                          LAB_CPU_GUARANTEE=p['lab_cpu_guarantee'],
                          TINY_MAX_CPU=p['tiny_max_cpu'],
                          MB_PER_CPU=p['mb_per_cpu'],
                          LAB_SIZE_RANGE=p['lab_size_range'],
                          AUTO_REPO_URLS=p['auto_repo_urls'],
                          ALLOW_DASK_SPAWN=p['allow_dask_spawn'],
                          SIZE_INDEX=p['size_index'],
                          HUB_ROUTE=p['hub_route'],
                          FIREFLY_ADMIN_PASSWORD=self.encode_value(
                              'firefly_admin_password'),
                          FIREFLY_REPLICAS=p['firefly_replicas'],
                          FIREFLY_CONTAINER_MEM_LIMIT=p[
                              'firefly_container_mem_limit'],
                          FIREFLY_CONTAINER_CPU_LIMIT=p[
                              'firefly_container_cpu_limit'],
                          FIREFLY_MAX_JVM_SIZE=p['firefly_max_jvm_size'],
                          FIREFLY_UID=p['firefly_uid'],
                          FIREFLY_ROUTE=p['firefly_route'],
                          RESTRICT_DASK_NODES=p['restrict_dask_nodes'],
                          RESTRICT_LAB_NODES=p['restrict_lab_nodes'],
                          DB_IDENTIFIER='{{DB_IDENTIFIER}}',
                          NFS_SERVER_IP_ADDRESS='{{NFS_SERVER_IP_ADDRESS}}',
                          )

    def _rename_fileserver_templates(self):
        """We did not finish substituting the fileserver, because
        we need the service address.
        """
        directory = os.path.join(self.directory, "deployment",
                                 "fileserver")
        fnbase = "jld-fileserver"
        for m in MTPTS:
            src = os.path.join(directory, fnbase + "-%s-pv.yml" % m)
            tgt = os.path.join(directory, fnbase + "-%s-pv.template.yml" % m)
            os.rename(src, tgt)

    def _rename_jupyterhub_template(self):
        """We did not finish subsituting JupyterHub, because we need the
        database identifier.
        """
        directory = os.path.join(self.directory, "deployment", "jupyterhub")
        src = os.path.join(directory, "jld-hub-deployment.yml")
        tgt = os.path.join(directory, "jld-hub-deployment.template-stage2.yml")
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
            # Cloud SQL isn't working yet.
            if False:
                self._create_database_instance()
                self._create_db_access_credentials()
                self._create_database()
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
            self._create_tls_secrets()
            if self.enable_firefly:
                self._create_firefly()
            self._substitute_db_identifier()
            self._create_jupyterhub()
            if self.enable_landing_page:
                self._create_landing_page()
            self._create_dns_record()

    def _create_gke_cluster(self):
        """Create cluster and namespace if required.  If cluster is created,
        create nginx ingress controller and external interface.
        """
        mtype = self.params['gke_machine_type']
        nodes = self.params['gke_node_count']
        dsize = self.params['gke_local_volume_size_gigabytes']
        name = self.params['kubernetes_cluster_name']
        namespace = self.params['kubernetes_cluster_namespace']
        clver = self._get_correct_k8s_version()
        if not self.existing_cluster:
            gcloud_parameters = ["container", "clusters", "create", name,
                                 "--num-nodes=%d" % nodes,
                                 "--machine-type=%s" % mtype,
                                 "--disk-size=%s" % dsize,
                                 "--cluster-version=%s" % clver,
                                 "--node-version=%s" % clver
                                 ]
            self._run_gcloud(gcloud_parameters)
            self._run_gcloud(["container", "clusters", "get-credentials",
                              name])
            self._create_admin_binding()
            self._create_nginx_ingress_controller()
        self._switch_to_context(name)
        if namespace != "default" and not self.existing_namespace:
            # This sometimes fails immediately after cluster creation,
            #  so run it under _waitfor()
            self._waitfor(self._create_namespace, delay=1, tries=15)

    def _create_database_instance(self):
        if self.existing_database_instance:
            dbiname = self._get_db_instance_name()
            self.params["database_instance_name"] = dbiname
            return
        dbiname = self.params['kubernetes_cluster_name']
        # Database name can't be reused for a week, hence the random
        #  string appended.  Must meet naming rules.
        randstr = self._generate_random_pw(len=8).lower()
        firstc = randstr[0]
        if firstc not in string.ascii_letters:
            randstr = "d" + randstr[1:]
        dbiname = dbiname + "-" + randstr
        self.params["database_instance_name"] = dbiname
        rc = self._run(["gcloud", "sql", "instances", "create",
                        dbiname, "--format=yaml", "--region",
                        self.params["gke_region"]], capture=True)
        if rc.stdout:
            result = yaml.safe_load(rc.stdout.decode('utf-8'))
            self._database = {}
            self._database["connectionName"] = result["connectionName"]
            for ips in result["ipAddresses"]:
                if ips["type"] == "PRIMARY":
                    self._database["ipAddress"] = ips["ipAddress"]
                    break

    def _destroy_database(self):
        self._destroy_database_db()
        self._destroy_database_instance()

    def _destroy_database_instance(self):
        if self.existing_database_instance:
            return
        self._destroy_db_access_credentials()
        dbiname = self.params.get('database_instance_name')
        if not dbiname:
            dbiname = self._get_db_instance_name(check=False)
        if dbiname:
            self._run(["gcloud", "sql", "instances", "delete", dbiname, "-q"])

    def _get_db_instance_name(self, check=True):
        rc = self._run(["gcloud", "sql", "instances", "list",
                        "--format=yaml"], capture=True)
        if rc.stdout:
            result = yaml.safe_load_all(rc.stdout.decode('utf-8'))
            prefix = self.params['kubernetes_cluster_name'] + "-"
            inamesall = [x['name'] for x in result]
            inames = [x for x in inamesall if x.startswith(prefix)]
            estr = ("candidate database names starting with '%s' found" %
                    prefix)
            if len(inames) == 0:
                if check:
                    raise RuntimeError("No %s." % estr)
                else:
                    logging.error("No %s." % estr)
                    return
            if len(inames) > 1:
                # This is always fatal even if check is False
                raise RuntimeError("Multiple %s: %s" % (estr, str(inames)))
            return inames[0]

    def _create_database(self):
        logging.info("Existing DB? %r" % self.existing_database)
        if self.existing_database:
            return
        self._run(["gcloud", "sql", "databases", "create",
                   self.params['kubernetes_cluster_namespace'],
                   "-i", self.params['database_instance_name']])

    def _destroy_database_db(self):
        if self.existing_database:
            return
        dbiname = self._get_db_instance_name(check=False)
        if not dbiname:
            return
        self.params['database_instance_name'] = dbiname
        self._run(["gcloud", "sql", "databases", "delete",
                   self.params['kubernetes_cluster_namespace'],
                   "-i", dbiname, "-q"])

    def _create_db_access_credentials(self):
        if self._check_for_db_sa():
            logging.info("Database service account already exists.")
            return
        sa_name = self.params["kubernetes_cluster_name"][:24] + "-db-sa"
        rc = self._run(["gcloud", "iam", "service-accounts", "create",
                        sa_name, "--display-name", sa_name, "--format=yaml"],
                       capture=True)
        if rc.stdout:
            result = yaml.safe_load(rc.stdout.decode('utf-8'))
            uid = result['uniqueId']
            email = result['email']
            self._database['sa'] = {}
            self._database['sa']['email'] = email
            self._database['sa']['uid'] = uid
            self._bind_db_service()
            self._create_db_proxyuser()
            self._create_sql_instance_credentials()
            self._create_db_credentials()

    def _check_for_db_sa(self):
        sa_email = (self.params["kubernetes_cluster_name"][:24] + "-db-sa@" +
                    self.params["gke_project"] + ".iam.gserviceaccount.com")
        rc = self._run(["gcloud", "iam", "service-accounts", "describe",
                        sa_email, "--format=yaml"], capture=True,
                       check=False)
        return (rc.returncode == 0)

    def _destroy_db_access_credentials(self):
        self._destroy_db_credentials()
        self._destroy_sql_instance_credentials()
        project = self.params['gke_project']
        saname = self.params['kubernetes_cluster_name'][:24] + "-db-sa"
        if not self._database:
            self._database = {}
        if not self._database.get('sa'):
            self._database['sa'] = {}
        if not self._database['sa'].get('email'):
            self._database['sa']['email'] = (saname + "@" + project +
                                             ".iam.gserviceaccount.com")
        email = self._database['sa']['email']
        self._unbind_db_service()
        self._run(["gcloud", "iam", "service-accounts", "delete", email, "-q"],
                  check=False)

    def _manipulate_db_service_account(self, verb, check=True):
        email = self._database['sa']['email']
        project = self.params['gke_project']
        self._run(["gcloud", "projects", verb,
                   project, "--member", "serviceAccount:" + email,
                   "--role=roles/cloudsql.editor"], check=check)

    def _bind_db_service(self):
        self._manipulate_db_service_account("add-iam-policy-binding")

    def _unbind_db_service(self):
        self._manipulate_db_service_account(
            "remove-iam-policy-binding", check=False)

    def _create_db_proxyuser(self):
        self._run(["gcloud", "sql", "users", "create", "proxyuser",
                   "cloudsqlproxy~%",
                   "--instance=%s" % self.params['database_instance_name'],
                   "--password=%s" % self.params['session_db_pw']])

    def _get_db_keys(self):
        email = self._database['sa']['email']
        keyh, keyf = tempfile.mkstemp()
        os.close(keyh)
        self._run(["gcloud", "iam", "service-accounts", "keys", "create",
                   keyf, "--iam-account", email])
        self._database['keyfile'] = keyf

    def _create_sql_instance_credentials(self):
        self._get_db_keys()
        keyf = self._database['keyfile']
        ns = self.params['kubernetes_cluster_namespace']
        self._run(["kubectl", "create", "secret", "generic",
                   "cloudsql-instance-credentials",
                   "--from-file=credentials.json=%s" % keyf,
                   "--namespace", ns])
        os.remove(keyf)
        self._database['keyfile'] = None
        del self._database['keyfile']

    def _destroy_sql_instance_credentials(self):
        self._run_kubectl_delete(["secret", "cloudsql-instance-credentials"])

    def _create_db_credentials(self):
        pw = self.params['session_db_pw']
        ns = self.params['kubernetes_cluster_namespace']
        self._run(["kubectl", "create", "secret", "generic",
                   "cloudsql-db-credentials",
                   "--from-literal=username=proxyuser",
                   "--from-literal=password=%s" % pw,
                   "--namespace", ns])

    def _destroy_db_credentials(self):
        self._run_kubectl_delete(["secret", "cloudsql-db-credentials"])

    def _create_nginx_ingress_controller(self):
        ns = "ingress-nginx"
        self._create_named_namespace(ns)
        ingdir = os.path.join(self.directory, "deployment", "nginx-ingress")
        ingfiles = [(os.path.join(ingdir, x) + ".yml") for x in
                    ["default-http-backend-deployment",
                     "default-http-backend-service",
                     "nginx-configuration-configmap",
                     "tcp-services-configmap",
                     "udp-services-configmap",
                     "nginx-ingress-serviceaccount",
                     "nginx-ingress-clusterrolebinding",
                     "nginx-ingress-clusterrole",
                     "nginx-ingress-role",
                     "nginx-ingress-rolebinding",
                     "nginx-ingress-controller-deployment",
                     "ingress-nginx-service"]]
        for ingf in ingfiles:
            self._run_kubectl_create_in_namespace(ingf, ns)

    def _destroy_nginx_ingress_controller(self):
        ns = "ingress-nginx"
        delitems = [["svc", "ingress-nginx-service"],
                    ["deployment", "nginx-ingress-controller"],
                    ["rolebinding", "nginx-ingress-role-nisa-binding"],
                    ["role", "nginx-ingress-role"],
                    ["clusterrolebinding",
                     "nginx-ingress-clusterrole-nisa-binding"],
                    ["clusterrole", "nginx-ingress", "clusterrole"],
                    ["serviceaccount", "nginx-ingress-serviceaccount"],
                    ["configmap", "udp-services"],
                    ["configmap", "tcp-services"],
                    ["configmap", "nginx-configuration"],
                    ["svc", "default-http-backend"],
                    ["deployment", "default-http-backend"]]
        for di in delitems:
            self._run_kubectl_delete_from_namespace(di, ns)
        self._destroy_namespace(ns, check=False)

    def _create_named_namespace(self, namespace):
        rc = self._run(["kubectl", "create", "namespace",
                        namespace],
                       check=False)
        if rc.returncode == 0:
            return True
        return False

    def _create_namespace(self):
        return self._create_named_namespace(
            self.params['kubernetes_cluster_namespace'])

    def _destroy_namespace(self, namespace, check=True):
        rc = self._run(["kubectl", "delete", "namespace", namespace],
                       check=check)
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
        struct = yaml.safe_load(rc.stdout.decode('utf-8'))
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
        """Destroy cluster, namespace, and ingress controller if required.
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
            self._destroy_namespace(namespace,
                                    check=self.existing_cluster)
        if not self.existing_cluster:
            self._destroy_nginx_ingress_controller()
            self._run_kubectl_delete(["clusterrolebinding", "admin-binding"])
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
                  ["svc", "logstashrmq"],
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
        for m in MTPTS:
            for c in ["jld-fileserver-%s-pv-%s.yml" % (m, ns),
                      "jld-fileserver-%s-pvc.yml" % m]:
                self._run_kubectl_create(os.path.join(directory, c))

    def _substitute_fileserver_ip(self, ip, ns):
        """Once we have the (internal) IP of the fileserver service, we
        can substitute it into the deployment template, but that requires the
        service to have been created first.
        """
        directory = os.path.join(self.directory, "deployment", "fileserver")
        for m in MTPTS:
            with open(os.path.join(directory,
                                   "jld-fileserver-%s-pv.template.yml" % m),
                      "r") as fr:
                tmpl = Template(fr.read())
                out = tmpl.render(NFS_SERVER_IP_ADDRESS=ip)
                ofn = "jld-fileserver-%s-pv-%s.yml" % (m, ns)
                with open(os.path.join(directory, ofn), "w") as fw:
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
            struct = yaml.safe_load(rc.stdout.decode('utf-8'))
            if not _empty(struct, "spec"):
                return struct["spec"]["clusterIP"]
        return None

    def _get_external_ip(self):
        """Get external IP of nginx service from YAML output.
        """
        ns = "ingress-nginx"
        rc = self._run(["kubectl", "get", "svc", "ingress-nginx",
                        "--namespace=%s" % ns,
                        "-o", "yaml"],
                       check=False,
                       capture=True)
        if rc.stdout:
            struct = yaml.safe_load(rc.stdout.decode('utf-8'))
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
        struct = yaml.safe_load(rc.stdout.decode('utf-8'))
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
        struct = yaml.safe_load(rc.stdout.decode('utf-8'))
        if "spec" in struct and "volumeName" in struct["spec"]:
            pv = struct["spec"]["volumeName"]
        if pv:
            logging.info("Getting disk name for PV '%s'." % pv)
            rc = self._run(["kubectl", "get", "pv", "-o", "yaml", pv],
                           capture=True, check=False)
            if rc.returncode != 0:
                return pv
            struct = yaml.safe_load(rc.stdout.decode('utf-8'))
            if ("spec" in struct and "gcePersistentDisk" in struct["spec"]
                    and "pdName" in struct["spec"]["gcePersistentDisk"]):
                disk = struct["spec"]["gcePersistentDisk"]["pdName"]
                self.disklist.append(disk)
        return pv

    def _destroy_fileserver(self):
        logging.info("Destroying fileserver.")
        ns = self.params["kubernetes_cluster_namespace"]
        pv = self._get_pv_and_disk_from_pvc("jld-fileserver-physpvc")
        items = []
        # Remove NFS PVCs and PVs
        for m in MTPTS:
            items.append(["pvc", "jld-fileserver-%s" % m])
        for m in MTPTS:
            items.append(["pv", "jld-fileserver-%s-%s" % (m, ns)])
        items.extend([["deployment", "jld-fileserver"],
                      ["svc", "jld-fileserver"],
                      ["pvc", "jld-fileserver-physpvc"]])
        if pv:
            items.append(["pv", pv])
        items.append(["storageclass", "fast"])
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

    def _create_admin_binding(self):
        user = self._get_account_user()
        self._run(["kubectl", "create", "clusterrolebinding",
                   "admin-binding", "--clusterrole=cluster-admin",
                   "--user=%s" % user])

    def _get_account_user(self):
        rc = self._run(["gcloud", "config", "get-value", "account"],
                       capture=True)
        user = rc.stdout.decode('utf-8').strip()
        return user

    def _create_landing_page(self):
        logging.info("Creating landing page")
        lp_dir = os.path.join(
            self.directory,
            "deployment",
            "landing-page")
        self._run_kubectl_create(os.path.join(
            lp_dir, "landing-page-service.yml"))
        self._run_kubectl_create(os.path.join(
            lp_dir, "landing-page-ingress.yml"))
        self._run(['kubectl', 'create', 'configmap', 'landing-page-www',
                   "--from-file=%s" % os.path.join(lp_dir, "config")])
        self._run_kubectl_create(os.path.join(
            lp_dir, "landing-page-deployment.yml"))

    def _destroy_landing_page(self):
        logging.info("Destroying landing page")
        self._run_kubectl_delete(["deployment", "landing-page"])
        self._run_kubectl_delete(["configmap", "landing-page-www"])
        self._run_kubectl_delete(["ingress", "landing-page"])
        self._run_kubectl_delete(["service", "landing-page"])

    def _create_prepuller(self):
        logging.info("Creating prepuller")
        pp_dir = os.path.join(
            self.directory,
            "deployment",
            "prepuller")
        self._run_kubectl_create(os.path.join(
            pp_dir, "prepuller-serviceaccount.yml"))
        self._run_kubectl_create(os.path.join(
            pp_dir, "prepuller-clusterrole.yml"))
        self._run_kubectl_create(os.path.join(
            pp_dir, "prepuller-role.yml"))
        self._run_kubectl_create(os.path.join(
            pp_dir, "prepuller-clusterrolebinding.yml"))
        self._run_kubectl_create(os.path.join(
            pp_dir, "prepuller-rolebinding.yml"))
        self._run_kubectl_create(os.path.join(pp_dir, "prepuller-cronjob.yml"))

    def _destroy_prepuller(self):
        logging.info("Destroying prepuller")
        self._run_kubectl_delete(["cronjob", "prepuller"])
        self._run_kubectl_delete(["rolebinding", "prepuller"])
        self._run_kubectl_delete(["clusterrolebinding", "prepuller"])
        self._run_kubectl_delete(["role", "prepuller"])
        self._run_kubectl_delete(["clusterrole", "prepuller"])
        self._run_kubectl_delete(["serviceaccount", "prepuller"])

    def _create_jupyterhub(self):
        logging.info("Creating JupyterHub")

        directory = os.path.join(self.directory, "deployment", "jupyterhub")
        for c in ["jld-hub-service.yml", "jld-hub-physpvc.yml",
                  "jld-hub-secrets.yml", "jld-hub-serviceaccount.yml",
                  "jld-hub-role.yml", "jld-hub-rolebinding.yml",
                  "jld-hub-ingress.yml", "jld-dask-serviceaccount.yml",
                  "jld-dask-role.yml", "jld-dask-rolebinding.yml"]:
            self._run_kubectl_create(os.path.join(directory, c))
        cfdir = os.path.join(directory, "config")
        cfnm = "jupyterhub_config"
        self._run(['kubectl', 'create', 'configmap', 'jld-hub-config',
                   "--from-file=%s" % os.path.join(cfdir, "%s.py" % cfnm),
                   "--from-file=%s" % os.path.join(cfdir, "%s.d" % cfnm)])
        self._run_kubectl_create(os.path.join(
            directory, "jld-hub-deployment.yml"))

    def _substitute_db_identifier(self):
        """Once we have the (internal) IP of the fileserver service, we
        can substitute it into the deployment template, but that requires the
        service to have been created first.
        """
        p = self.params
        directory = os.path.join(self.directory, "deployment", "jupyterhub")
        with open(os.path.join(directory,
                               "jld-hub-deployment.template-stage2.yml"),
                  "r") as fr:
            if not p.get('database_instance_name'):
                p['database_instance_name'] = "dummy"
            db_identifier = (p['gke_project'] + ":" + p['gke_region'] + ":" +
                             p['database_instance_name'])
            tmpl = Template(fr.read())
            out = tmpl.render(DB_IDENTIFIER=db_identifier)
            ofn = "jld-hub-deployment.yml"
            with open(os.path.join(directory, ofn), "w") as fw:
                fw.write(out)

    def _destroy_jupyterhub(self):
        logging.info("Destroying JupyterHub")
        pv = self._get_pv_and_disk_from_pvc("jld-hub-physpvc")
        items = [["rolebinding", "jld-dask"],
                 ["role", "jld-dask"],
                 ["serviceaccount", "jld-dask"],
                 ["ingress", "jld-hub"],
                 ["deployment", "jld-hub"],
                 ["configmap", "jld-hub-config"],
                 ["rolebinding", "jld-hub"],
                 ["role", "jld-hub"],
                 ["serviceaccount", "jld-hub"],
                 ["secret", "jld-hub"],
                 ["pvc", "jld-hub-physpvc"],
                 ["svc", "jld-hub"]]
        if pv:
            items.append(["pv", pv])
        for c in items:
            self._run_kubectl_delete(c)

    def _create_firefly(self):
        logging.info("Creating Firefly")
        directory = os.path.join(self.directory, "deployment", "firefly")
        for c in ["firefly-service",
                  "firefly-secrets",
                  "firefly-deployment",
                  "firefly-ingress"]:
            self._run_kubectl_create(os.path.join(directory, c + ".yml"))

    def _destroy_firefly(self):
        logging.info("Destroying Firefly")
        items = [["ingress", "firefly"],
                 ["deployment", "firefly"],
                 ["secret", "firefly"],
                 ["svc", "firefly"]]
        for c in items:
            self._run_kubectl_delete(c)

    def _create_tls_secrets(self):
        logging.info("Creating TLS secrets")
        directory = os.path.join(self.directory, "deployment", "tls")
        self._run_kubectl_create(os.path.join(directory, "tls-secrets.yml"))

    def _destroy_tls_secrets(self):
        logging.info("Destroying TLS secrets")
        self._run_kubectl_delete(["secret", "tls"])

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
            self._destroy_landing_page()
            self._destroy_jupyterhub()
            self._destroy_firefly()
            self._destroy_tls_secrets()
            self._destroy_prepuller()
            self._destroy_fs_keepalive()
            self._destroy_fileserver()
            self._destroy_logging_components()
            # CloudSQL doesn't work yet.
            if False:
                self._destroy_database()
            self._destroy_gke_cluster()
            self._destroy_gke_disks()

    def _run_gcloud(self, args, check=True, capture=False):
        """Convenience method for running gcloud in the right zone.
        """
        newargs = (["gcloud"] +
                   args +
                   ["--zone=%s" % self.params["gke_zone"]] +
                   ["--format=yaml"])
        if not self._empty_param("gke_project"):
            newargs = newargs + ["--project=%s" % self.params["gke_project"]]
        return self._run(newargs, check=check, capture=capture)

    def _run_kubectl_create_in_namespace(self, filename, namespace):
        """Convenience method to create a resource in a namespace.
        """
        self._run(['kubectl', 'create', '-f', filename, "--namespace=%s" %
                   namespace])

    def _run_kubectl_create(self, filename):
        """Convenience method to create a kubernetes resource from a file.
        """
        ns = self.params["kubernetes_cluster_namespace"]
        self._run_kubectl_create_in_namespace(filename, ns)

    def _run_kubectl_delete_from_namespace(self, component, namespace):
        """Convenience method to delete a resource from a namespace.
        Note that "component" is a two-item list, where the first item
        is a string indicating the resource type, and the second item
        is a string indicating its name.
        """
        self._run(['kubectl', 'delete'] + component +
                  ['--namespace=%s' % namespace],
                  check=False)

    def _run_kubectl_delete(self, component):
        """Convenience method to delete a kubernetes resource.
        """
        ns = self.params["kubernetes_cluster_namespace"]
        self._run_kubectl_delete_from_namespace(component, ns)

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
            self._rename_fileserver_templates()
            self._rename_jupyterhub_template()
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
    desc += ("The 'forbidden_groups' parameter, 'cilogon_group_denylist'," +
             "\n'github_organization_denylist', and 'auto_repo_urls' " +
             "follow the same format." +
             "\nThe denylist and URL list are optional and default to the " +
             "empty string.\n\n")
    desc += ("The 'auto_repo_urls' parameter, if supplied, is a list of " +
             "'git clone' URLs;\nat startup time, these repositories will " +
             "be synchronized and the 'prod'\nbranch brought up to date.\n\n")
    desc += ("The 'allow_dask_spawn' parameter, if supplied and set to a " +
             "non-empty string, will allow user containers to spawn " +
             "additional pods; this is intended to allow them to " +
             "manipulate dask workers.\n\n")
    desc += ("The 'size_index' parameter, if supplied, is the index of " +
             "the default image size--usually '1' indicating the " +
             "second-smallest.\n\n")
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
    pr.add_argument(
        "--existing-database-instance", help=("Do not create/destroy " +
                                              "database instance.  " +
                                              "Respected for undeployment " +
                                              "as well."),
        action='store_true')
    pr.add_argument(
        "--existing-database", help=("Do not create/destroy database.  " +
                                     "Respected for undeployment as well.  " +
                                     "Requires --existing-database-instance."),
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
    arurls = "auto_repo_urls"
    if not _empty(params, arurls):
        aru = params[arurls]
        if type(aru) is not str:
            params[arurls] = ','.join(aru)
    else:
        params[arurls] = "https://github.com/lsst-sqre/notebook-demo"
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
    dlname = "github_organization_denylist"
    if params["oauth_provider"] == "cilogon":
        dlname = "cilogon_group_denylist"
    if _empty(params, dlname):
        if not _empty(params, "forbidden_groups"):
            params[dlname] = params["forbidden_groups"]
    if not _empty(params, dlname):
        odl = params[dlname]
        if type(odl) is str:
            params[dlname] = odl.split(',')
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
    e_s = options.existing_database
    e_i = options.existing_database_instance
    e_n = options.existing_namespace
    e_d = options.directory
    c_c = options.create_config
    t_t = options.temporary
    p_p = None
    if "params" in options:
        p_p = options.params
    import pprint
    s = pprint.pformat(options)
    logging.info("Options: %s" % s)
    deployment = JupyterLabDeployment(yamlfile=y_f,
                                      disable_prepuller=d_p,
                                      existing_cluster=e_c,
                                      existing_namespace=e_n,
                                      existing_database=e_s,
                                      existing_database_instance=e_i,
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
    e_i = options.existing_database_instance
    e_d = options.existing_database
    p_p = None
    if "params" in options:
        p_p = options.params
    deployment = JupyterLabDeployment(yamlfile=y_f,
                                      existing_cluster=e_c,
                                      existing_namespace=e_n,
                                      existing_database_instance=e_i,
                                      existing_database=e_d,
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
