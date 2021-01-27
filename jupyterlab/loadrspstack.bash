# This script is intended to be used with bash to load the RSP clone of
#  the minimal LSST environment
# Usage: source loadrspstack.bash

export LSST_CONDA_ENV_NAME="rsp-$(source ${LOADSTACK} && \
				 echo "${LSST_CONDA_ENV_NAME}")"
source ${LOADSTACK} # Uses modified LSST_CONDA_ENV_NAME
