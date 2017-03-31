#!/bin/bash
source /usr/bin/virtualenvwrapper.sh \
&& workon jupyterlab \
&& jupyter lab --no-browser --debug --ip=* --notebook-dir=/home/jupyterlab/data

