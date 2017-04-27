#!/bin/bash
set -x
source /opt/lsst/software/stack/loadLSST.bash
source eups-setups.sh
setup lsst_distrib
if [ -e ${HOME}/.user_setups ]; then
    source ${HOME}/.user_setups
fi
exec python -m ipykernel -f $1
