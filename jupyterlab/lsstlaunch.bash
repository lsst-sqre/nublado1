#!/bin/bash
set -x
source /opt/lsst/software/stack/loadLSST.bash
source eups-setups.sh
setup lsst_distrib
<<<<<<< HEAD:jupyterlab/lsstlaunch.bash
uset=${HOME}/.user_setups
if [ -e ${uset} ]; then
    source ${uset}
=======
if [ -e ${HOME}/.user_setups ]; then
    source ${HOME}/.user_setups
>>>>>>> tickets/DM-10335:jupyterlab/lsstlaunch.sh
fi
exec python -m ipykernel -f $1
