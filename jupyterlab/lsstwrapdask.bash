#!/bin/bash
set -e

DASK_THREADS=${DASK_THREADS:-"2"}
DASK_MEM_LIMIT=${DASK_MEM_LIMIT:-"2GB"}
DASK_DEATH_TIMEOUT=${DASK_DEATH_TIMEOUT:-"60"}

LOADSTACK=/opt/lsst/software/stack/loadLSST.bash

source ${LOADSTACK}
exec dask-worker --nthreads ${DASK_THREADS} --no-bokeh \
     --memory-limit ${DASK_MEM_LIMIT} --death-timeout ${DASK_DEATH_TIMEOUT}

