# Terraform configuration for LSST Science Platform Notebook Aspect

This will eventually be the correct way to deploy an instance of the
LSST Science Platform Notebook Aspect.

Functional parity with the homebrew deployment tool is gated behind
Terraform 0.12, which is not yet released at the time of writing.

At the moment, it does work, but with the following caveats:

1. You have to run `terraform apply` twice to get the
   roles/rolebindings/serviceaccounts instantiated properly.
   
2. The binary configmap for the static landing page is not correctly
   created, so you will need to manually replace it.  Instructions are in
   the landing page deployment YAML.
   
3. It assumes an external fileserver and does not create any of the ELK
   logging components.

## Required deployment information

The easiest way to get the appropriate values into the Terraform
deployment is to set a number of `TF_VAR` environment variables, as well
as the AWS deployment credentials.  A sample sourceable shell file might
look like this:

```bash
export TF_VAR_allowed_groups="allowed-group1,allowed-group2"
export TF_VAR_forbidden_groups="forbidden-group"
export TF_VAR_gcloud_account="email@example.com"
export TF_VAR_gke_project="angry-hamster-22345"
export TF_VAR_hostname="endpoint-of-notebook-aspect.example.com"
export TF_VAR_oauth_client_id="precreate-this-at-github"
export TF_VAR_oauth_secret="precreate-this-at-github-too"
export TF_VAR_tls_dir="${HOME}/path/to/tls/directory"
export TF_VAR_aws_zone_id="route53-zone-id-for-domain"
export TF_VAR_external_fileserver_ip="ipaddress.of.nfs.server"
export TF_VAR_firefly_replicas="1"
export AWS_ACCESS_KEY_ID="aws-access-key"
export AWS_SECRET_ACCESS_KEY="aws-secret-key"
```

Then you would just source that file before running `terraform apply`.
