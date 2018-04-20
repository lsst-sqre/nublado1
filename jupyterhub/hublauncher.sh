#!/bin/bash
USER=jupyter
GROUP=jupyter
HOMEDIR=/home/${USER}
if ! [ -d ${HOMEDIR} ]; then
    mkdir -p ${HOMEDIR}
fi
if ! [ -f ${HOMEDIR}/jupyterhub.sqlite ]; then
    touch ${HOMEDIR}/jupyterhub.sqlite
fi
chmod 0600 ${HOMEDIR}/jupyterhub.sqlite
chown -R ${USER}:${GROUP} ${HOMEDIR}
cd ${HOMEDIR}
export HUB_BIND_IP=$(/sbin/ifconfig | grep 'inet ' | awk '{print $2}' | \
			 grep -v '127.0.0.1' | head -1)
dbgflag=""
jhdir="/opt/lsst/software/jupyterhub"
conf="${jhdir}/config/jupyterhub_config.py"
if [ -n "${DEBUG}" ]; then
    dbgflag="--debug "
fi
upgdb="--upgrade-db"
source scl_source enable rh-python36
cmd="sudo -E -u ${USER} ${jhdir}/hubwrapper.sh ${upgdb} ${dbgflag} -f ${conf}"
if [ -n "${DEBUG}" ]; then
    ${cmd}
    sleep 600
else
    exec $cmd
fi
