#!/bin/bash

. virtualenvwrapper.sh
workon py3
exec jupyterhub --debug -f ${HOME}/jupyterhub_config.py
