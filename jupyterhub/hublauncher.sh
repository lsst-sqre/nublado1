#!/bin/bash

# Don't run as root
if [ $(id -u) -eq 0 ]; then
    echo 1>&2 "Fatal: running as UID 0."
    echo 1>&2 "Sleeping to prevent respawn spamming."
    sleep 60
    exit 2
fi

# Set working directory
cd ${HOME}

# Create sqlite DB if necessary, and protect it.
dbtype=$(echo ${SESSION_DB_URL} | cut -d ':' -f 1)
if [ "${dbtype}" == "sqlite" ]; then
    if ! [ -f ${HOME}/jupyterhub.sqlite ]; then
        touch ${HOME}/jupyterhub.sqlite
    fi
    chmod 0600 ${HOME}/jupyterhub.sqlite
fi

# Set up command-line arguments
dbgflag=""
if [ -n "${DEBUG}" ]; then
    dbgflag="--debug "
fi
jhdir="/opt/lsst/software/jupyterhub"
conf="${jhdir}/config/jupyterhub_config.py"
if [ -f "${HOME}/jupyterhub-proxy.pid" ]; then
    rm "${HOME}/jupyterhub-proxy.pid"
fi
cmd="/usr/local/bin/jupyterhub ${dbgflag} -f ${conf}"

# Start Hub
if [ -n "${DEBUG}" ]; then
    ${cmd}
    sleep 600
else
    exec $cmd
fi
