#!/bin/bash
export PATH=/opt/conda/bin:$PATH
jupyterhub --debug -f /home/jupyterlab/jupyterhub_config.py
