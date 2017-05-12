#!/bin/bash
if [ -n "${DEBUG}" ]; then
    set -x
fi
cmd="python /usr/bin/jupyter-singlelabuser \
     --ip='*' --port=8888 --debug \
     --hub-api-url=${JPY_HUB_API_URL} \
     --notebook-dir=${HOME}/notebooks \
     --LabApp.base_url=/user/${USER}"
echo ${cmd}
if [ -n "${DEBUG}" ]; then
    ${cmd}
    sleep 3600
else
    exec ${cmd}
fi

