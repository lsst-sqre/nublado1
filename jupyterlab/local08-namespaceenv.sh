#!/bin/sh
extracted=$(echo $JUPYTERHUB_API_URL | cut -d '/' -f 3)
JUPYTERHUB_NAMESPACE=$(echo ${extracted} | cut -d '.' -f 2 | cut -d ':' -f 1)
LSP_INSTANCE=$(echo ${extracted} | cut -d '.' -f 1 | sed -e 's/-hub//')
if [ -n "${INSTANCE_NAME}" ]; then
    if [ "${INSTANCE_NAME}" != "${LSP_INSTANCE}" ]; then
	echo 1>&2 "INSTANCE NAME and LSP_INSTANCE differ!"
	echo 1>&2 "'${INSTANCE_NAME}' != '${LSP_INSTANCE}'!"
    fi
fi
export JUPYTERHUB_NAMESPACE LSP_INSTANCE
