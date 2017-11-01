"""Bootstrapper configuration for JupyterHub
Based on:

https://github.com/yuvipanda/jupyterhub-singlenode-deploy/blob/master/modules/jupyterhub/files/bootstrap_config.py

Looks for all files inside the directory specified by the environment
variable 'JUPYTERHUB_CONFIG_DIR'.  If that variable is not set,
'jupyterhub_config.d' is used.

If the directory name does not start with '/' it is assumed to be relative to
the location of this file.  Once the directory is determined, we load all
the .py files inside it. This allows us to have small modular config files
instead of one monolithic one.

The filenames should be of form NN-something.py, where NN is a two
digit priority number. The files will be loaded in ascending order of
NN. Filenames not ending in .py will be ignored.
"""
import os
from glob import glob

dirname = os.getenv('JUPYTERHUB_CONFIG_DIR') or 'jupyterhub_config.d'
if dirname[0] != '/':
    confdir = os.path.join(os.path.dirname(os.path.abspath(__file__)), dirname)

for f in sorted(glob(os.path.join(confdir, '*.py'))):
    load_subconfig(f)
