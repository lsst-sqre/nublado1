#!/bin/bash

. virtualenvwrapper.sh
workon py3
exec sudo -E /usr/bin/jupyterhub --debug -f /home/jupyterlab/jupyterhub_config.py
