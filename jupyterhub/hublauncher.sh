#!/bin/bash
function primecache {
    cachefile="${HOME}/repo-cache.json"
    owner="${LAB_REPO_OWNER:-lsstsqre}"
    name="${LAB_REPO_NAME:-sciplat-lab}"
    host="${LAB_REPO_HOST:-hub.docker.com}"
    experimentals="${PREPULLER_EXPERIMENTALS:-0}"
    dailies="${PREPULLER_DAILIES:-3}"
    weeklies="${PREPULLER_WEEKLIES:-2}"
    releases="${PREPULLER_RELEASES:-1}"
    dbg=""
    if [ -n "${DEBUG}" ]; then
	dbg="-d "
    fi
    scanrepo -j ${dbg}-f ${cachefile} -r ${host} -o ${owner} -n ${name} \
	     -e ${experimentals} -w ${weeklies} -q ${dailies} \
	     -b ${releases} 2>&1 >/dev/null
}

if [ $(id -u) -eq 0 ]; then
    echo 1>&2 "Warning: running as UID 0."
    echo 1>&2 "Sleeping to prevent respawn spamming."
    sleep 60
    exit 2
fi
cd ${HOME}
dbtype=$(echo ${SESSION_DB_URL} | cut -d ':' -f 1)
if [ "${dbtype}" == "sqlite" ]; then
    if ! [ -f ${HOME}/jupyterhub.sqlite ]; then
        touch ${HOME}/jupyterhub.sqlite
    fi
    chmod 0600 ${HOME}/jupyterhub.sqlite
fi
echo "Priming repo cache in background..."
primecache &
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
