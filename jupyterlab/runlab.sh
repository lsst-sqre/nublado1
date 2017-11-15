#!/bin/sh
# Set to turn on debugging
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
for i in notebooks DATA WORK idleculler; do
    mkdir -p "${HOME}/${i}"
done
# Fetch/update magic notebook.
. /opt/lsst/software/jupyterlab/refreshnb.sh
# Run idle culler.
if [ -n "${JUPYTERLAB_IDLE_TIMEOUT}" ] && \
       [ "${JUPYTERLAB_IDLE_TIMEOUT}" -gt 0 ]; then
    touch ${HOME}/idleculler/culler.output && \
	nohup python3 /opt/lsst/software/jupyterlab/selfculler.py >> \
              ${HOME}/idleculler/culler.output 2>&1 &
fi
cmd="python3 /usr/bin/jupyter-labhub \
     --ip='*' --port=8888 --debug \
     --hub-api-url=${JUPYTERHUB_API_URL} \
     --notebook-dir=${HOME}/notebooks"
echo ${cmd}
if [ -n "${DEBUG}" ]; then
    # Spin while waiting for interactive container use.
    while : ; do
        d=$(date)
        echo "${d}: sleeping."
        sleep 60
    done
else
    # Start Lab
    exec ${cmd}
fi
