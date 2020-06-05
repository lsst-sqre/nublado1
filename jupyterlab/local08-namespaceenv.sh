#!/bin/sh
extracted=$(echo $JUPYTERHUB_API_URL | cut -d '/' -f 3)
JUPYTERHUB_NAMESPACE=$(echo ${extracted} | cut -d '.' -f 2 | cut -d ':' -f 1)
LSP_INSTANCE=$(echo ${extracted} | cut -d '.' -f 1 | sed -e 's/-hub//')
export JUPYTERHUB_NAMESPACE LSP_INSTANCE
