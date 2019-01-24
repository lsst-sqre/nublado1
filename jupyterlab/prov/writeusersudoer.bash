#!/bin/bash

function usage() {
    local me=$0
    echo 1>&2 "Usage: ${me} USERNAME"
}

function write_user_sudoer() {
    local username=$1
    local sudoers="/etc/sudoers.d/88_jupyter"
    local labdir="/opt/lsst/software/jupyterlab"
    l="provisionator ALL = (${username}) NOPASSWD:SETENV: ${labdir}/runlab.sh"
    echo "${l}" > ${sudoers}
}

## Begin mainline code. ##
if [ -n "${DEBUG}" ]; then
    set -x
fi
username=$1
shift
if [ -z "${username}" ] || [ -n "$1" ] ; then
    usage
    exit 2
fi
write_user_sudoer ${username}
