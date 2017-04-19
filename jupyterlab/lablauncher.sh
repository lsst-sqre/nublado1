#!/bin/bash

function setup_user() {
    id -u ${JPY_USER} 2> /dev/null 1>&2
    if [ $? -ne 0 ]; then
	make_user
    fi
}

function make_user() {
    # If GITHUB_ID is not set, then we rely on sqrekubespawner/GHOWLAuth
    #  to have named the pod correctly.  Failing that we just use the
    #  standard system generated UID.
    # We would like the pod named jupyter-<user>-<githubid>
    # If we can get a good value, the UID and GID will both be that.
    local nuid=""
    if [ -z "${GITHUB_ID}" ]; then
	last=$(hostname | cut -d '-' -f 3)
	case ${last} in
	    ''|*[!0-9]*)
		GITHUB_ID=""
		;;
	    *)
		GITHUB_ID=${last}
		;;
	esac
    fi
    # Reject implausibly small values.  Probably means
    #  regular kubespawner, and thus we got "1"
    if [ "${GITHUB_ID}" -lt 10 ]; then
	GITHUB_ID=""
    fi
    if [ -n "${GITHUB_ID}" ]; then
	nuid="-u ${GITHUB_ID} -N -g ${GITHUB_ID} -s /bin/bash"
	groupadd -g ${GITHUB_ID} ${JPY_USER}
    fi
    adduser -m ${JPY_USER} -c '' ${nuid}
    create_git_credentials
}

function create_git_credentials() {
    if [ -n "${GITHUB_ACCESS_TOKEN}" ]; then
	local entry="https://${JPY_USER}:${GITHUB_ACCESS_TOKEN}@github.com"
	local file="/home/${JPY_USER}/.git-credentials"
	local gitcfg="/home/${JPY_USER}/.gitconfig"
	echo "${entry}" > ${file}
	chmod 0600 ${file}
	chown ${JPY_USER}:${JPY_USER} ${file}
	echo "[credential]" > ${gitcfg}
	echo "    helper = store" >> ${gitcfg}
    fi
}

## Begin mainline code. ##
set -x
sudo=""
if [ $(id -u) -eq 0 ]; then
    if [ -n "${JPY_USER}" ]; then
	setup_user
	sudo="sudo -E -u ${JPY_USER} "
    else
	echo 1>&2 "Warning: running as UID 0"
    fi
fi
exec ${sudo} /opt/lsst/software/jupyterlab/runlab.sh
