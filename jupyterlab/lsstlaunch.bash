#!/bin/bash
set -x
source /opt/lsst/software/stack/loadLSST.bash
source eups-setups.sh
setup lsst_distrib
uset=${HOME}/.user_setups
if [ -e ${uset} ]; then
    source ${uset}
fi
exec python -m ipykernel -f $1
