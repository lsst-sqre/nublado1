#!/bin/bash

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

function manage_access_token() {
    local tokfile="${HOME}/.access_token"
    # Clear it out each new interactive lab start.
    rm -f "${tokfile}"
    # Try the configmap first, and if that fails, use the environment
    #  variable (which eventually will go away)
    local instance_tok="/opt/lsst/software/jupyterhub/tokens/${FQDN}-token"
    if [ -e  "${instance_tok}" ]; then
	ln -s "${instance_tok}" "${tokfile}"
    elif [ -n "${ACCESS_TOKEN}" ]; then
	echo "${ACCESS_TOKEN}" > "${tokfile}"
    fi
}

function copy_lsst_dask() {
    mkdir -p "${HOME}/.config/dask"
    cp "/opt/lsst/software/jupyterlab/lsst_dask.yml" "${HOME}/.config/dask/"
}

function create_dask_yml() {
    # Try the configmap first.  As with access_token, there's one per
    #  instance.
    local fname="${FQDN}-dask_worker.example.yml"
    local dtl="/opt/lsst/software/jupyterhub/dask_yaml/${fname}"
    local dh="${HOME}/dask"
    mkdir -p "${dh}"
    local dw="${dh}/dask_worker.yml"
    if [ -e "${dtl}" ]; then
	rm -f "${dw}"
	rm -f "${dh}/${fname}"
	cp "${dtl}" "${dw}"
	ln -s "${dtl}" "${dh}/${fname}"
    else
	template_dask_file
    fi
}

function template_dask_file() {
    # Do it the hard way (will be removed eventually)
    # Overwrite any existing template.
    local dw="${HOME}/dask/dask_worker.yml"
    mkdir -p "${HOME}/dask"
    local debug="\'\'"
    if [ -n "${DEBUG}" ]; then
        debug=${DEBUG}
    fi
    # Work around MEM_GUARANTEE bug
    local mb_guarantee=${MEM_GUARANTEE}
    local lastchar="$(echo ${mb_guarantee} | tail -c 1)"
    case lastchar in
	[0-9]) mb_guarantee="${mb_guarantee}M"
	       ;;
	*)
	       ;;
    esac
    sed -e "s|{{JUPYTER_IMAGE_SPEC}}|${JUPYTER_IMAGE_SPEC}|" \
        -e "s/{{EXTERNAL_GROUPS}}/${EXTERNAL_GROUPS}/" \
        -e "s/{{EXTERNAL_UID}}/${EXTERNAL_UID}/" \
        -e "s/{{JUPYTERHUB_USER}}/${JUPYTERHUB_USER}/" \
        -e "s/{{CPU_LIMIT}}/${CPU_LIMIT}/" \
        -e "s/{{MEM_LIMIT}}/${MEM_LIMIT}/" \
        -e "s/{{CPU_GUARANTEE}}/${CPU_GUARANTEE}/" \
        -e "s/{{MEM_GUARANTEE}}/${mb_guarantee}/" \
        -e "s/{{DEBUG}}/${debug}/" \
        /opt/lsst/software/jupyterlab/dask_worker.template.yml \
        > "${dw}"
    # Add mounts
    echo -n "${DASK_VOLUME_B64}" | base64 -d >> "${dw}"
    # Add restriction
    if [ -n "${RESTRICT_DASK_NODES}" ]; then
        mv ${dw} ${dw}.unrestricted
        sed -e "s/# nodeSelector:/nodeSelector:/" \
	    -e "s/#   dask: ok/  dask: ok/" \
	    ${dw}.unrestricted > ${dw} && \
	    rm ${dw}.unrestricted
    fi
    cp "${dw}"
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

function start_noninteractive() {
    cmd='/opt/lsst/software/jupyterlab/noninteractive/noninteractive'
    echo "Starting noninteractive container: ${cmd}"
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
# Unset SUDO env vars so that Conda doesn't misbehave
unset SUDO_USER SUDO_UID SUDO_GID SUDO_COMMAND
# Add paths
source /etc/profile.d/local05-path.sh
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
NODE_OPTIONS=${NODE_OPTIONS:-"--max-old-space-size=7168"}
export NODE_OPTIONS
sync
cd ${HOME}
# Do /etc/skel copy (in case we didn't provision homedir but still need to
#  populate it)
copy_etc_skel
# Replace API URL with service address if it exists
if [ -n "${HUB_SERVICE_HOST}" ]; then
    jh_proto=$(echo $JUPYTERHUB_API_URL | cut -d '/' -f -1)
    jh_path=$(echo $JUPYTERHUB_API_URL | cut -d '/' -f 4-)
    port=${HUB_SERVICE_PORT_API}
    if [ -z "${port}" ]; then
        port=${HUB_SERVICE_PORT}
        if [ -z "${port}" ]; then
            port="8081"
        fi
    fi
    jh_api="${jh_proto}//${HUB_SERVICE_HOST}:${port}/${jh_path}"
    JUPYTERHUB_API_URL=${jh_api}
fi
export JUPYTERHUB_API_URL
# Set Firefly URL and landing page
if [ -z "${EXTERNAL_URL}" ]; then
    EXTERNAL_URL=${EXTERNAL_INSTANCE_URL}
    export EXTERNAL_URL
fi
host_url=$(echo ${EXTERNAL_URL} | cut -d '/' -f 1-3)
FIREFLY_ROUTE=${FIREFLY_ROUTE:-"/firefly/"}
FIREFLY_URL="${host_url}${FIREFLY_ROUTE}"
if [ -n "${EXTERNAL_FIREFLY_URL}" ]; then
    FIREFLY_URL=${EXTERNAL_FIREFLY_URL}
fi
FIREFLY_HTML="slate.html"
export FIREFLY_URL FIREFLY_HTML
if [ -z "${JUPYTERHUB_SERVICE_PREFIX}" ]; then
    # dask.distributed gets cranky if it's not there (since it is used
    #  in lsst_dask.yml); it will be for interactive use, and whether
    #  or not the proxy dashboard URL is correct doesn't matter in a
    #  noninteractive context.
    JUPYTERHUB_SERVICE_PREFIX="/nb/user/${JUPYTERHUB_USER}"
    export JUPYTERHUB_SERVICE_PREFIX
fi
if [ -n "${DASK_WORKER}" ]; then
    start_dask_worker
    exit 0 # Not reached
elif [ -n "${NONINTERACTIVE}" ]; then
    start_noninteractive
    exit 0 # Not reached
else
    # Create dask yml if we are an interactive Lab and not a worker
    copy_lsst_dask
    create_dask_yml
    # Manage access token (again, only if we are a Lab)
    manage_access_token
    # Fetch/update magic notebook.
    . /opt/lsst/software/jupyterlab/refreshnb.sh
    # Clear eups cache.  Use a subshell.
    ( source /opt/lsst/software/stack/loadLSST.bash && \
	  eups admin clearCache )
fi
# The Rubin Lap App plus our environment should get the right hub settings
cmd="jupyter-rubinlab \
     --ip='*' \
     --port=8888 \
     --no-browser \
     --notebook-dir=${HOME} \
     --LabApp.shutdown_no_activity_timeout=43200 \
     --MappingKernelManager.cull_idle_timeout=43200 \
     --MappingKernelManager.cull_connected=True \
     --FileContentsManager.hide_globs=[] \
     --KernelSpecManager.ensure_native_kernel=False"
#     --SingleUserNotebookApp.hub_api_url=${EXTERNAL_INSTANCE_URL}${JUPYTERHUB_SERVER_PREFIX}
#     --SingleUserNotebookApp.hub_prefix=${JUPYTERHUB_SERVICE_PREFIX}
#     --SingleUserNotebookApp.hub_host=${EXTERNAL_INSTANCE_URL}
if [ -n "${DEBUG}" ]; then
    cmd="${cmd} --debug"
fi
# echo "----JupyterLab env----"
# env | sort
# echo "----------------------"
# echo "JupyterLab command: '${cmd}'"
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
source ${LOADRSPSTACK}
exec ${cmd}
