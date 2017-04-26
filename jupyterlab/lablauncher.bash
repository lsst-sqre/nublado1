#!/bin/bash

function setup_user() {
    id -u ${U_NAME} 2> /dev/null 1>&2
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
    # If GITHUB_ORGANIZATIONS is set to a comma-separated list of name:id
    #  tuples, we create those groups, and then we put supplementary groups on
    #  the user.
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
    local create="-m"
    if [ -d "/home/${U_NAME}" ]; then
	# Shared storage?  Maybe homedir is already there.
	create="-M"
    fi
    if [ -n "${GITHUB_ID}" ]; then
	nuid="-u ${GITHUB_ID} -N -g ${GITHUB_ID}"
    fi
    make_user_groups
    local suppgr=""
    if [ -n "${GITHUB_ORGANIZATIONS}" ]; then
	local ght=""
	local ghn=""
	for ght in $(echo ${GITHUB_ORGANIZATIONS} | tr "," "\n"); do
	    ghn=$(echo ${ght} | cut -d ':' -f 1)
	    if [ -z "${suppgr}" ]; then
		suppgr=$"-G ${ghn}"
	    else
		suppgr="${suppgr},${ghn}"
	    fi
	done
	
    fi
    adduser ${create} ${U_NAME} -c "${GITHUB_NAME}" ${nuid} -s /bin/bash \
	    ${suppgr}
    create_git_config
}

function make_group() {
    local gname=$1
    local gid=$2
    local grp=$(getent group ${gname})
    local grid=$(getent group ${gid})
    local gidstr=""
    if [ -z "${grp}" ]; then
	if [ -z "${grid}" ]; then
	    gidstr="-g ${gid}"
	fi
	groupadd ${gidstr} ${gname}
    fi
}
    
function make_user_groups() {
    if [ -n "${GITHUB_ID}" ]; then
	make_group ${U_NAME} ${GITHUB_ID}
    fi
    if [ -n "${GITHUB_ORGANIZATIONS}" ]; then
	# We have set this to a comma-separated list of name:id tuples.
	local ght=""
	local ghn=""
	local ghid=""
	for ght in $(echo ${GITHUB_ORGANIZATIONS} | tr "," "\n"); do
	    ghn=$(echo ${ght} | cut -d ':' -f 1)
	    ghid=$(echo ${ght} | cut -d ':' -f 2)
	    make_group ${ghn} ${ghid}
	done
    fi	    
}

function create_git_config() {
    local file="/home/${U_NAME}/.git-credentials"
    local gitcfg="/home/${U_NAME}/.gitconfig"
    # Do not clobber existing files...or symlinks, or dirs, or ...
    #  If it's there, assume it's intentional.
    if ! [ -e ${file} ]; then
	if [ -n "${GITHUB_ACCESS_TOKEN}" ]; then
	    local entry="https://${U_NAME}:${GITHUB_ACCESS_TOKEN}"
	    entry="${entry}@github.com"
	    echo "${entry}" > ${file}
	    chmod 0600 ${file}
	    chown ${U_NAME}:${U_NAME} ${file}
	fi
    fi
    if ! [ -e ${gitcfg} ]; then
	local userheader=""
	if [ -n "${GITHUB_NAME}" ]; then
	    userheader=1
	    echo "[user]" > ${gitcfg}
	    echo "    name = ${GITHUB_NAME}" >> ${gitcfg}
	fi
	if [ -n "${GITHUB_EMAIL}" ]; then
	    if [ -z "${userheader}" ]; then
		echo "[user]" > ${gitcfg}
		userheader=1
	    fi
	    echo "    email = ${GITHUB_EMAIL}" >> ${gitcfg}
	fi
	if [ -z "${userheader}" ]; then
	    touch ${gitcfg}
	else
	    echo "" >> ${gitcfg}
	fi
	echo "[credential]" >> ${gitcfg}
	echo "    helper = store" >> ${gitcfg}
	chown ${U_NAME}:${U_NAME} ${gitcfg}
    fi
}

function unset_extraneous_vars() {
    local var
    for var in GITHUB_ACCESS_TOKEN JPY_API_TOKEN \
	       KUBERNETES_PORT KUBERNETES_PORT_443_TCP \
               KUBERNETES_PORT_443_TCP_ADDR KUBERNETES_PORT_443_TCP_PORT \
	       KUBERNETES_PORT_443_TCP_PROTO KUBERNETES_SERVICE_HOST \
	       KUBERNETES_SERVICE_PORT KUBERNETES_SERVICE_PORT_HTTPS \
	       ; do
	unset ${var}
    done
}

## Begin mainline code. ##
sudo=""
U_NAME="${JPY_USER}" # I expect JPY_USER to become something else.
WORKDIR="/tmp"
if [ $(id -u) -eq 0 ]; then
    if [ -n "${U_NAME}" ]; then
	setup_user
	sudo="sudo -E -u ${U_NAME} "
	WORKDIR="/home/${U_NAME}"
    else
	echo 1>&2 "Warning: running as UID 0"
    fi
fi
cd ${WORKDIR}
unset_extraneous_vars
exec ${sudo} /opt/lsst/software/jupyterlab/runlab.bash
