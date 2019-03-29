#!/bin/bash
if [ $(id -u) -eq 0 ]; then
    echo 1>&2 "Warning: running as UID 0."
    echo 1>&2 "Sleeping to prevent respawn spamming."
    sleep 60
    exit 2
fi
cd ${HOME}
dbtype=$(echo ${SESSION_DB_URL} | cut -d ':' -f 1)
if [ "${dbtype}" == "sqlite" ]; then
    if ! [ -f ./jupyterhub.sqlite ]; then
        touch ./jupyterhub.sqlite
    fi
    chmod 0600 ./jupyterhub.sqlite
fi
dbgflag=""
jhdir="/opt/lsst/software/jupyterhub"
conf="${jhdir}/config/jupyterhub_config.py"
if [ -n "${DEBUG}" ]; then
    dbgflag="--debug "
fi
if [ -f "${HOME}/jupyterhub-proxy.pid" ]; then
    rm "${HOME}/jupyterhub-proxy.pid"
fi
cmd="/usr/local/bin/jupyterhub ${dbgflag} -f ${conf}"
echo $cmd
if [ -n "${DEBUG}" ]; then
    ${cmd}
    sleep 600
else
    exec $cmd
fi
