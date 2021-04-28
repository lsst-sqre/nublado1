#!/bin/bash
CONFIG_FILE=$1
# /opt/lsst/sal only exists in SAL builds of the stack
if [ -d /opt/lsst/sal ]; then
    source /opt/lsst/sal/salbldsteps.bash 2>&1 > /dev/null
    for i in xml idl sal salobj ATDome ATDomeTrajectory ATMCSSimulator \
            simactuators standardscripts scriptqueue externalscripts ; do
        setup ts_${i} -t current
    done
else
    source /opt/lsst/software/stack/loadLSST.bash
    setup lsst_distrib
fi
setup display_firefly
if [ -e ${HOME}/notebooks/.user_setups ]; then
    source ${HOME}/notebooks/.user_setups
fi
exec python3 -m ipykernel -f ${CONFIG_FILE}

