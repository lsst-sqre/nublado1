#!/bin/bash
set -x
source /opt/lsst/software/stack/loadLSST.bash
setup lsst_distrib
if [ -e ${HOME}/notebooks/.user_setups ]; then
    source ${HOME}/notebooks/.user_setups
fi
exec python3 -m ipykernel -f $1
