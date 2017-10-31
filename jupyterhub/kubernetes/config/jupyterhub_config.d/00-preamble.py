"""
This is the JupyterHub configuration directory that LSST DM-SQuaRE uses.

Different subconfiguration files in this directory do different things.
The major components are the options form, the spawner, the authenticator,
 and the assembly of those components into a configuration.

These files are mapped into the JupyterHub configuration as a ConfigMap.
Feel free to edit them to suit your needs.
The location is specified in the deployment file:
 jld-hub-config/jld-hub-cfg.py ->
  /opt/lsst/software/jupyterhub/config/jupyterhub_config.py
 jld-hub-config/jld-hub-cfg-dir ->
  /opt/lsst/software/jupyterhub/config/jupyterhub_config.d
"""
