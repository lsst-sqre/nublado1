#!/bin/bash

function usage() {
    local me=$0
    echo 1>&2 "Usage: ${me} USERNAME"
}

function change_staging_id() {
    # JupyterLab wants to rebuild the index for extensions.
    # If the files it wants exist and are owned by another user, it fails
    #  even if they are writeable.
    local username=$1
    local stagedir="/opt/rh/rh-python36/root/usr/lib/python3.6"
    stagedir="${stagedir}/site-packages/jupyterlab/staging"
    for i in package.json index.js webpack.config.js; do
	chown ${username} "${stagedir}/${i}"
    done
        chown ${username} "${stagedir}"
}

username=$1
shift
if [ -z "${username}" ] || [ -n "${1}"] ; then
    usage
    exit 2
fi
change_staging_id ${username}

