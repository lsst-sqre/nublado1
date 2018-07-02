#!/bin/bash
CONFIG_FILE=$1
source /opt/lsst/software/stack/loadLSST.bash
setup lsst_distrib
setup display_firefly
if [ -e ${HOME}/notebooks/.user_setups ]; then
    source ${HOME}/notebooks/.user_setups
fi
exec python3 -m ipykernel -f ${CONFIG_FILE}

