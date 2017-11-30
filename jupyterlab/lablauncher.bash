#!/bin/bash

function setup_user() {
    id -u ${U_NAME} 2> /dev/null 1>&2
    if [ $? -ne 0 ]; then
	make_user
    fi
    change_staging_id
    setup_git
}

function make_user() {
    # If EXTERNAL_UID is not set, we just use the standard system generated
    #  UID.
    # If we can get a good value, the UID and GID will both be that.
    # Reject implausibly small values.  Probably means we didn't get an
    #  ID and so we get the (small) serial assigned by KubeSpawner
    local nuid=""
    if [ "${EXTERNAL_UID}" -lt 100 ]; then
	EXTERNAL_UID=""
    fi
    if [ -n "${EXTERNAL_UID}" ]; then
	nuid="-u ${EXTERNAL_UID} -g ${U_NAME}"
    fi
    add_groups
    local gentry=""
    local suppgrp="-G jupyter"
    if [ -n "${EXTERNAL_GROUPS}" ]; then
	for gentry in $(echo ${EXTERNAL_GROUPS} | tr "," "\n"); do
	    gname=$(echo ${gentry} | cut -d ':' -f 1)
	    if [ -z "${gname}" ]; then
		continue
	    fi
	    if [ -z "${suppgrp}" ]; then
		suppgrp="-G ${gname}"
	    else
		suppgrp="${suppgrp},${gname}"
	    fi
	done
    fi
    homedir="${HOMEDIRS}/${U_NAME}"
    makedir="-m"
    if [ -e "${homedir}" ]; then
	makedir="-M"
    fi
    adduser ${U_NAME} -d ${homedir} -c '' -N -g ${U_NAME} ${nuid} \
      ${suppgrp} ${makedir} -s ${DEFAULT_SHELL}
}

function add_groups() {
    add_group ${U_NAME} ${EXTERNAL_UID}
    local gentry=""
    local gname=""
    local gid=""
    if [ -n "${EXTERNAL_GROUPS}" ]; then
        for gentry in $(echo ${EXTERNAL_GROUPS} | tr "," "\n"); do
            gname=$(echo ${gentry} | cut -d ':' -f 1)
            gid=$(echo ${gentry} | cut -d ':' -f 2)
            add_group ${gname} ${gid}
        done
    fi
}

function add_group() {
    # If the group exists already, use that.
    # If it doesn't exist but the group id is in use, use a system-
    #  assigned gid.
    # Otherwise, use the group id to create the group.
    local gname=$1
    local gid=$2
    local exgrp=$(getent group ${gname})
    if [ -n "${exgrp}" ]; then
        return
    fi
    if [ -n "${gid}" ]; then
        local exgid=$(getent group ${gid})
        if [ -n "${exgid}" ]; then
            gid=""
        fi
    fi
    local gopt=""
    if [ -n "${gid}" ]; then
        gopt="-g ${gid}"
    fi
    groupadd ${gopt} ${gname}
}

function forget_extraneous_vars() {
    local purge="GITHUB_ACCESS_TOKEN MEM_LIMIT CPU_LIMIT"
    unset ${purge}
    purge_docker_vars KUBERNETES HTTPS:443
    purge_docker_vars K8S_JLD_NGINX HTTP:80,HTTPS:443
    purge_docker_vars JLD_FILESERVER RPCBIND:111,NFS:2049,MOUNTD:20048
}

function purge_docker_vars() {
    local n=$1
    local plist=$2
    local purge="${n}_PORT"
    local portmap=""
    local portname=""
    local portnum=""
    local i=""
    local k=""
    for i in "HOST" "PORT"; do
	purge="${purge} ${n}_SERVICE_${i}"
    done
    for portmap in $(echo ${plist} | tr "," "\n"); do
        portname=$(echo ${portmap} | cut -d ':' -f 1)
	purge="${purge} ${n}_SERVICE_PORT_${portname}"
        portnum=$(echo ${portmap} | cut -d ':' -f 2)
	for prot in "TCP" "UDP"; do
	    k="${n}_PORT_${portnum}_${prot}"
	    purge="${purge} ${k}"
	    for i in "ADDR" "PORT" "PROTO"; do
		purge="${purge} ${k}_${i}"
	    done
	done
    done
    unset ${purge}
}

function setup_git() {
    # Always remove old token and overwrite with latest credentials.
    # That way if we change permissions on our scope, the old (possibly
    # more permissive) one doesn't hang around.
    local file="${HOMEDIRS}/${U_NAME}/.git-credentials"
    rm -f ${file} 2>/dev/null || /bin/true
    if [ -n "${GITHUB_ACCESS_TOKEN}" ]; then
        local entry="https://${U_NAME}:${GITHUB_ACCESS_TOKEN}@github.com"
        echo "${entry}" > ${file}
        chmod 0600 ${file}
        chown ${U_NAME}:${U_NAME} ${file}
    fi
    local gitcfg="${HOMEDIRS}/${U_NAME}/.gitconfig"
    if [ ! -e "${gitcfg}" ]; then
	touch ${gitcfg}
	echo "[push]" >> ${gitcfg}
	echo "    default = simple" >> ${gitcfg}
        echo "[credential]" >> ${gitcfg}
        echo "    helper = store" >> ${gitcfg}
        chown ${U_NAME}:${U_NAME} ${gitcfg}
    fi
}

function change_staging_id() {
    # JupyterLab wants to rebuild the index for extensions.
    # If the files it wants exist and are owned by another user, it fails
    #  even if they are writeable.
    local stagedir="/usr/share/jupyter/lab/staging"
    for i in package.json index.js webpack.config.js; do
	chown ${U_NAME} "${stagedir}/${i}"
    done
}

## Begin mainline code. ##
U_NAME="${JUPYTERHUB_USER}"
HOMEDIRS="/home"
DEFAULT_SHELL="/bin/bash"
TOPDIR="/opt/lsst"
sudo=""
if [ $(id -u) -eq 0 ]; then
    if [ -n "${U_NAME}" ]; then
	setup_user
	sudo="sudo -E -u ${U_NAME} "
    else
	echo 1>&2 "Warning: running as UID 0"
    fi
fi
forget_extraneous_vars
exec ${sudo} ${TOPDIR}/software/jupyterlab/runlab.sh
