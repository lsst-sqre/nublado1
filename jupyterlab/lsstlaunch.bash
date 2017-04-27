#!/bin/bash
set -x
source /opt/lsst/software/stack/loadLSST.bash
source eups-setups.sh
setup lsst_distrib
uset=${HOME}/.user_setups
if [ -e ${uset} ]; then
    source ${uset}
if [ -e ${HOME}/notebooks/.user_setups ]; then
    source ${HOME}/notebooks/.user_setups
fi
exec python -m ipykernel -f $1
