#!/bin/sh
function setup_git() {
    # If we have a token, remove old token and update with new one.
    # That way if we change permissions on our scope, the old (possibly
    # more permissive) one doesn't hang around.
    if [ -n "${GITHUB_ACCESS_TOKEN}" ]; then
        local file="${HOME}/.git-credentials"
        local gitname=${GITHUB_LOGIN:-$USER}
        local regex="|^https://${gitname}.*@github.com\$|d"
        sed -i '' -e ${regex} ${file}
        local entry="https://${gitname}:${GITHUB_ACCESS_TOKEN}@github.com"
        echo "${entry}" >> ${file}
        chmod 0600 ${file}
        unset GITHUB_ACCESS_TOKEN
    fi
}

function create_dask_yml() {
    # Overwrite any existing template.
    mkdir -p "${HOME}/dask"
    local debug="\'\'"
    if [ -n "${DEBUG}" ]; then
	debug=${DEBUG}
    fi
    sed -e "s|{{JUPYTER_IMAGE_SPEC}}|${JUPYTER_IMAGE_SPEC}|" \
        -e "s/{{EXTERNAL_GROUPS}}/${EXTERNAL_GROUPS}/" \
        -e "s/{{EXTERNAL_UID}}/${EXTERNAL_UID}/" \
        -e "s/{{JUPYTERHUB_USER}}/${JUPYTERHUB_USER}/" \
        -e "s/{{CPU_LIMIT}}/${CPU_LIMIT}/" \
        -e "s/{{MEM_LIMIT}}/${MEM_LIMIT}/" \
        -e "s/{{CPU_GUARANTEE}}/${CPU_GUARANTEE}/" \
        -e "s/{{MEM_GUARANTEE}}/${MEM_GUARANTEE}/" \
	-e "s/{{DEBUG}}/${debug}/" \
        /opt/lsst/software/jupyterlab/dask_worker.template.yml \
        > "${HOME}/dask/dask_worker.yml"
}

function clear_dotlocal() {
    local dotlocal="${HOME}/.local"
    local now=$(date +%Y%m%d%H%M%S)
    if [ -d ${dotlocal} ]; then
        mv ${dotlocal} ${dotlocal}.${now}
    fi
}

function copy_etc_skel() {
    es="/etc/skel"
    for i in $(find ${es}); do
        if [ "${i}" == "${es}" ]; then
            continue
        fi
        b=$(echo ${i} | cut -d '/' -f 4-)
        hb="${HOME}/${b}"
        if ! [ -e ${hb} ]; then
            cp -a ${i} ${hb}
        fi
    done
}

function start_dask_worker() {
    cmd='/opt/lsst/software/jupyterlab/lsstwrapdask.bash'
    echo "Starting dask worker: ${cmd}"
    exec ${cmd}
    exit 0 # Not reached
}

# Set DEBUG to a non-empty value to turn on debugging
if [ -n "${DEBUG}" ]; then
    set -x
fi
# Clear $HOME/.local if requested
if [ -n "${CLEAR_DOTLOCAL}" ]; then
    clear_dotlocal
fi
# Set up SCLs
source /etc/profile.d/local06-scl.sh
# Set GitHub configuration
setup_git
if [ -n "${GITHUB_EMAIL}" ]; then
    git config --global --replace-all user.email "${GITHUB_EMAIL}"
fi
if [ -n "${GITHUB_NAME}" ]; then
    git config --global --replace-all user.name "${GITHUB_NAME}"
fi
# Initialize git LFS
grep -q '^\[filter "lfs"\]$' ${HOME}/.gitconfig
rc=$?
if [ ${rc} -ne 0 ]; then
    git lfs install
fi
# Bump up node max storage to allow rebuild
NODE_OPTIONS=--max-old-space-size=4096
export NODE_OPTIONS
sync
cd ${HOME}
# Do /etc/skel copy (in case we didn't provision homedir but still need to
#  populate it)
copy_etc_skel
# Fetch/update magic notebook.
. /opt/lsst/software/jupyterlab/refreshnb.sh
# Replace API URL with service address if it exists
if [ -n "${JLD_HUB_SERVICE_HOST}" ]; then
    jh_proto=$(echo $JUPYTERHUB_API_URL | cut -d '/' -f -1)
    jh_path=$(echo $JUPYTERHUB_API_URL | cut -d '/' -f 4-)
    port=${JLD_HUB_SERVICE_PORT_API}
    if [ -z "${port}" ]; then
        port="8081"
    fi
    jh_api="${jh_proto}//${JLD_HUB_SERVICE_HOST}:${port}/${jh_path}"
    JUPYTERHUB_API_URL=${jh_api}
fi
export JUPYTERHUB_API_URL
# Set Firefly URL and landing page
host_url=$(echo ${EXTERNAL_URL} | cut -d '/' -f 1-3)
FIREFLY_ROUTE=${FIREFLY_ROUTE:-"/firefly/"}
FIREFLY_URL="${host_url}${FIREFLY_ROUTE}"
FIREFLY_HTML="slate.html"
export FIREFLY_URL FIREFLY_HTML
if [ -n "${DASK_WORKER}" ]; then
    start_dask_worker
    exit 0 # Not reached
else
    # Create dask worker yml if we are a Lab and not a worker
    create_dask_yml
fi
cmd="jupyter-labhub \
     --ip='*' --port=8888 \
     --hub-api-url=${JUPYTERHUB_API_URL} \
     --notebook-dir=${HOME}"
if [ -n "${DEBUG}" ]; then
    cmd="${cmd} --debug"
fi
echo "JupyterLab command: '${cmd}'"
# Run idle culler.
if [ -n "${JUPYTERLAB_IDLE_TIMEOUT}" ] && \
   [ "${JUPYTERLAB_IDLE_TIMEOUT}" -gt 0 ]; then
     touch ${HOME}/idleculler/culler.output && \
       nohup python3 /opt/lsst/software/jupyterlab/selfculler.py >> \
             ${HOME}/idleculler/culler.output 2>&1 &
fi
if [ -n "${DEBUG}" ]; then
    # Spin while waiting for interactive container use.
    while : ; do
        ${cmd}
        d=$(date)
        echo "${d}: sleeping."
        sleep 60
    done
    exit 0 # Not reached
fi
# Start Lab
exec ${cmd}
