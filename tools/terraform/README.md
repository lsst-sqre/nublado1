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
