#!/bin/bash
set -x
source /opt/lsst/software/stack/loadLSST.bash
source eups-setups.sh
setup lsst_distrib
exec python -m ipykernel -f $1
