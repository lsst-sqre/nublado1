# Automated JupyterLab Demo Deployment

## Basic Usage

These instructions should suffice to get you going with an LSST
JupyterLab Demo environment, where all of the following conditions are
true.

- The computation is hosted within Google Kubernetes Engine.
- The domain name is hosted within AWS Route 53.
- Authentication is done via OAuth against GitHub, and GitHub
  organization membership is used to determine access control.
- Authentication via OAuth against NCSA/CILogon is also supported.

Here are the steps you need to perform:

1. Choose a fully-qualified domain name in a domain that you control and
   that is hosted by AWS Route 53.  The FQDN need not exist, as long as
   you have write access to the domain that contains it at Route 53.

2. Go to GitHub.  Decide what organizations you want to allow as your
   whitelist, and which organization should own the OAuth callback
   (presumably that organization will be in the whitelist).  You must
   have administrative privileges over the organization.
   
    1. Go to that organization's page and click on `Settings`.
    2. Go to `OAuth Apps` under `Developer Settings`.
	3. Click on `New OAuth App`.
	4. The Application Name is probably something to do with
       JupyterLab.  The `Homepage URL` is just `https://` prepended to the
       FQDN you chose above plus the route to the Hub (usually `/nb/`).
	   The Authorization callback URL is the `Homepage URL` prepended to
       `/hub/oauth_callback`. 
    5. Note the Client ID and Client Secret you get.  You will need
       these later.
	   
	If you're using CILogon, set up your client and secret using NCSA as
    your identity provider.  The whitelist will be a comma-separated
	list of NCSA groups.  You can also provide denylists for either
    GitHub or CILogon; if a user is present in a denylisted group,
    login will be denied regardless of whether the user is in a
    whitelisted group.

3. Get TLS certificates for the hostname you provided above.  AWS
   certificates will not work, as you need the TLS private key for the
   JupyterLab setup.  A wildcard certificate for the domain would work
   fine.  I do not think a self-signed certificate will work, because
   the GitHub callback will (correctly) note that the certificate chain
   is untrusted.  Certificates from letsencrypt.org work fine, although
   that will take setup that is not yet part of the automated
   deployment.  Put the following files (in PEM format) in a directory
   on the machine you are running the deployment from:
   
    - TLS Certificate (cert.pem)
	- TLS Key (key.pem)
	- TLS Root Chain (chain.pem)
	   
4. Make sure that your shell environment is set up to allow `gcloud`,
   `kubectl`, and `aws` to run authenticated.  This will require `gcloud
   init`, `aws configure`, and `kubectl`.  On MacOS the brew version of
   `kubectl` is generally slightly ahead of the `kubectl` component of
   `gcloud`.  In order to allow the landing page deployment to use a
   binary ConfigMap for its static content, you will require `kubectl`
   version `1.10` or later.

5. Create a Python virtualenv with Python3 as its interpreter.  This
   step is not strictly necessary but will keep you from cluttering up
   your system python with the modules required for deployment.
   
   Python 3.5 or later is necessary: this deployment will not work with
   Python 2 or Python 3.0-3.4.

    - I like to use `virtualenv-wrapper` and `mkvirtualenv`; if you're
   doing that, `mkvirtualenv -p $(which python3)` (you will need to have
   started a shell with the `mkvirtualenv` alias available first).
   
   - Without `virtualenv-wrapper` you would do something like `python3
   -m venv /path/to/environment` followed by `source
   /path/to/environment/bin/activate`.

    - Without a virtual environment you will need to use the `--user`
    option on the `pip3` command below.

6. Change to a working directory you like and clone this repository
   (`git clone https://github.com/lsst-sqre/sqre-jupyterlabdemo`).
   
7. `cd sqre/jupyterlabdemo/tools/deployment`.  Then (making sure you are
   inside the activated virtualenv) `pip3 install -e .`.  If you chose
   to not use virtualenv, `pip3 install --user -e .`.

### Interactive deployment

8. Run `deploy-jupyterlabdemo`.  Answer the questions asked by the
deployment script (FQDN, certificate directory, OAuth client and secret,
and whitelist of GitHub Organizations or CILogon Groups).  If you want to
use CILogon you should set the environment variable
`JLD_OAUTH_PROVIDER` to `cilogon` before running the deployment tool.


### YAML document-based / Environment-based deployment

8. (alternate) `cp example-deployment.yml mydeploy.yml`.  Edit
    `mydeploy.yml`. The following settings are required:
    - `hostname`: the FQDN from earlier.
    - `tls_cert`, `tls_key`, and `tls_root_chain`.  These correspond to
      the TLS PEM files you got earlier: specify the (local) path to
      them.
    - `oauth_client_id` and `oauth_secret` from the OAuth
      application you created earlier.
	- `oauth_provider`: `github` or `cilogon`.
	- `allowed_groups`: each list entry is the name of a GitHub
      Organization or CILogon/NCSA Group.  Or you can set:
        - `github_organization_whitelist` or
        - `cilogon_group_whitelist`
	  
   You can also specify these as environment variables.  The rule for
   creation is that the environment variable name is `JLD_` prepended to
   the uppercase representation of the setting name, so you'd need, for
   instance, `JLD_HOSTNAME`.  If you run the deployment
   program without either specifying a file or supplying required
   parameters in the environment, you will be prompted for those
   parameters as in the interactive deployment.
   
   The default `kubernetes_cluster_name` is the DNS FQDN with dots
   replaced by dashes.  The default `kubernetes_cluster_namespace` is
   the first component of the hostname.  These can be changed in the
   deployment YAML or through environment variables.

   If `external_fileserver_ip` is set, that IP address will be used;
   this (at least currently) must be an NFSv4 fileserver which will
   allow a client to both create new directories on the remote volume
   (mounted in the Lab container as `/home`) and change their
   ownership.  If this parameter is not set, a fileserver container (and
   backing storage) and a keepalive container will be created and
   used.  You may want to change the volume size from its default of
   20Gb with the parameter `volume_size_gigabytes`.

   Feel free to customize other settings.  You particularly may want to
   change the volume size, and I strongly recommend precreating your
   `dhparam.pem` file with `openssl dhparam 2048 > dhparam.pem` in the
   same directory as the rest of your TLS files, and then enabling it in
   the deployment YAML.  All deployment settings can also be represented
   in the environment, but optional settings will not be
   prompted--instead, defaults will be used.

   Finally, run `deploy-jupyterlabdemo -f /path/to/mydeploy.yml` .

### Usage and teardown

9. After installation completes, browse to the FQDN you created.

10. When you're done and ready to tear down the cluster, run
    `deploy-jupyterlabdemo -f /path/to/mydeploy.yml -u` if you deployed
    with a YAML file, or just `deploy-jupyterlabdemo -u` and answer the
	FQDN question if `JLD_HOSTNAME` is not set.

## Running a custom configuration

1. Specify a directory you want the configuration to be built in with
   `deploy-jupyterlabdemo -f /path/to/mydeploy.yml -d
   /path/to/config/directory -c`
   
2. Edit the Kubernetes deployment files under
   `/path/to/config/directory`.  For instance, you may want to change
   the environment variables the JupyterHub component uses to deploy a
   different JupyterLab image, or indeed you may want to change the
   JupyterHub ConfigMap files to change the authentication or spawner
   configuration.
   
3. Deploy with `deploy-jupyterlabdemo -f /path/to/mydeploy.yml -d
   /path/to/config/directory`
   
## Preserving existing clusters and namespaces.

If you do not want to create and destroy a new cluster each time, you
can use the `--existing-cluster` parameter to `deploy-jupyterlabdemo`.
If you have specified `--existing-cluster` you can also use
`--existing-namespace`.  Both of these settings can also be used during
undeployment to leave the cluster (and namespace) at GKE.  If not
specified the cluster and namespace are created during deployment and
destroyed during undeployment.

   
