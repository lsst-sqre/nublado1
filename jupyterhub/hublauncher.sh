#!/bin/bash
USER=jupyter
GROUP=jupyter
HOMEDIR=/home/${USER}
if ! [ -d ${HOMEDIR} ]; then
    mkdir -p ${HOMEDIR}
    chown -R ${USER}:${GROUP} ${HOMEDIR}
fi
cd ${HOMEDIR}
export HUB_CONNECT_IP=$(/sbin/ifconfig | grep 'inet ' | awk '{print $2}' | \
			    grep -v '127.0.0.1')
exec sudo -E -u ${USER} /usr/bin/jupyterhub --debug -f \
      /opt/lsst/software/jupyterhub/jupyterhub_config.py
