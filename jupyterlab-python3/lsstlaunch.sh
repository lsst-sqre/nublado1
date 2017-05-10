#!/bin/bash
PY_VER=$1
CONN_FILE=$2
source /opt/lsst/software/stack/loadLSST.bash
setup lsst_distrib
if [ -e ${HOME}/notebooks/.user_setups ]; then
    source ${HOME}/notebooks/.user_setups
fi
exec python${PY_VER} -m ipykernel -f ${CONN_FILE}
