#!/bin/bash
set -e

INT_CPU=${CPU_LIMIT%.*}
DASK_THREADS=${DASK_THREADS:-${INT_CPU:-"2"}}
DASK_MEM_LIMIT=${DASK_MEM_LIMIT:-${MEM_LIMIT:-"2GB"}}
DASK_DEATH_TIMEOUT=${DASK_DEATH_TIMEOUT:-"60"}

LOADRSPSTACK=/opt/lsst/software/rspstack/loadrspstack.bash
TMPDIR=${TMPDIR:-"/tmp"}
# We don't want this on NFS.
DASK_LOCAL_DIR="${TMPDIR}/$(hostname)"
mkdir -p ${DASK_LOCAL_DIR}

source ${LOADRSPSTACK}
exec dask-worker --nthreads ${DASK_THREADS} \
     --memory-limit ${DASK_MEM_LIMIT} \
     --death-timeout ${DASK_DEATH_TIMEOUT} \
     --local-directory ${DASK_LOCAL_DIR}

