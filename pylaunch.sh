#!/bin/bash
set -x
echo "Args: $1 $2"
export PATH=/opt/conda/bin:$PATH
source activate $1
source eups-setups.sh
setup lsst_distrib
/usr/local/bin klaunch $2
