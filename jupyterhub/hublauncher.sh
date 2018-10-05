#!/bin/bash
USER=jupyter
GROUP=jupyter
HOMEDIR=/home/${USER}
if ! [ -d ${HOMEDIR} ]; then
    mkdir -p ${HOMEDIR}
fi
dbtype=$(echo ${SESSION_DB_URL} | cut -d ':' -f 1)
if [ "${dbtype}" == "sqlite" ]; then
    if ! [ -f ${HOMEDIR}/jupyterhub.sqlite ]; then
        touch ${HOMEDIR}/jupyterhub.sqlite
    fi
    chmod 0600 ${HOMEDIR}/jupyterhub.sqlite
fi
chown -R ${USER}:${GROUP} ${HOMEDIR}
cd ${HOMEDIR}
dbgflag=""
jhdir="/opt/lsst/software/jupyterhub"
conf="${jhdir}/config/jupyterhub_config.py"
if [ -n "${DEBUG}" ]; then
    dbgflag="--debug "
fi
if [ -f "/home/jupyter/jupyterhub-proxy.pid" ]; then
    rm /home/jupyter/jupyterhub-proxy.pid
fi
#upgdb="--upgrade-db"
upgdb=""
source scl_source enable rh-python36
cmd="sudo -E -u ${USER} ${jhdir}/hubwrapper.sh ${upgdb} ${dbgflag} -f ${conf}"
if [ -n "${DEBUG}" ]; then
    ${cmd}
    sleep 600
else
    exec $cmd
fi
