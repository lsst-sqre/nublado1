#!/bin/sh
#export DEBUG=1
if [ -n "${DEBUG}" ]; then
    set -x
fi
if [ -n "${GITHUB_EMAIL}" ]; then
    git config --global --replace-all user.email "${GITHUB_EMAIL}"
fi
if [ -n "${GITHUB_NAME}" ]; then
    git config --global --replace-all user.name "${GITHUB_NAME}"
fi
sync
cd ${HOME}
# Create standard dirs
for i in notebooks DATA WORK; do
    mkdir -p "${HOME}/${i}"
done
# Fetch/update magic notebook.
. /opt/lsst/software/jupyterlab/refreshnb.sh
# Run idle culler.
if [ -n "${JUPYTERLAB_IDLE_TIMEOUT}" ] && \
       [ "${JUPYTERLAB_IDLE_TIMEOUT}" -gt 0 ]; then
    nohup python3 /opt/lsst/software/jupyterlab/cull_idle_servers.py \
	  --timeout ${JUPYTERLAB_IDLE_TIMEOUT} > /tmp/culler.output \
	  2>&1 &
fi
hub_api="http://${JLD_HUB_SERVICE_HOST}:${JLD_HUB_SERVICE_PORT_API}/hub/api"
#cmd="python3 /usr/bin/jupyter-singlelabuser \
cmd="python3 /usr/bin/jupyter-labhub \
     --ip='*' --port=8888 --debug \
     --hub-api-url=${hub_api} \
     --notebook-dir=${HOME}/notebooks"
echo ${cmd}
if [ -n "${DEBUG}" ]; then
    while : ; do
        d=$(date)
        echo "${d}: sleeping."
        sleep 60
    done
else    
    exec ${cmd}
fi
