#!/bin/bash

function usage() {
    local me=$0
    echo 1>&2 "Usage: ${me} -n USERNAME [ -u UID ] [ -g GROUPS ]"
    echo 1>&2 " "
    echo 1>&2 " GROUPS: group1:gid1,group2:gid2,..."
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
    # We are already running inside sudo context
    groupadd ${gopt} ${gname}
}

function add_lab_user() {
    # Already in sudo context
    #  variables should have been populated during argument parsing
    add_groups
    adduser ${username} -d ${homedir} -c '' -N -g ${username} ${nuid} \
      ${suppgrp} ${makedir} -s ${default_shell}
}

function add_groups() {
    add_group ${username} ${external_uid}
    local gentry=""
    local gname=""
    local gid=""
    if [ -n "${external_groups}" ]; then
        for gentry in $(echo ${external_groups} | tr "," "\n"); do
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
    # Already in sudo context
    groupadd ${gopt} ${gname}
}


## Begin mainline code. ##
homedirs="/home"
default_shell="/bin/bash"
suppgrp="-G jupyter"
username=""
external_uid=""
external_groups=""
while getopts "h?n:u:g:" opt; do
    case "${opt}" in
	h|\?)
	    usage
	    exit 0
	    ;;
	n)
	    username=$OPTARG
	    ;;
	g)
	    external_groups=$OPTARG
	    ;;
	u)  external_uid=$OPTARG
	    ;;
    esac
done

shift $((OPTIND-1))

if [ -z "${username}" ]; then
    echo 2>&1 "Username is required!"
    exit 2
fi
if [ -n "${external_groups}" ]; then
    for gentry in $(echo ${external_groups} | tr "," "\n"); do
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
if [ -n "${external_uid}" ]; then
    if [ "${external_uid}" -lt 100 ]; then
	external_uid=""
    fi
    if [ -n "${external_uid}" ]; then
	nuid="-u ${external_uid} -g ${username}"
    fi
fi 
homedir="${homedirs}/${username}"
if [ -e "${homedir}" ]; then
    makedir="-M"
fi
add_lab_user
