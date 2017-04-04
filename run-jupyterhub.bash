#!/bin/bash
source /usr/bin/virtualenvwrapper.sh \
&& workon jupyterlab \
&& jupyterhub -f /home/jupyterlab/jupyterhub_config.py
