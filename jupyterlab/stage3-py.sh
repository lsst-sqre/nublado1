#!/bin/sh
set -e
# It looks like the conda env should also manage to install all our
#  pip dependencies as well.

#This commented-out bit, plus changing the definition of LOADRSPSTACK in
# Dockerfile.template, will clone the environment rather than installing
# into the stack environment itself.  This adds 50% or so to the container
# size.
#
# source ${LOADSTACK}
# rspname="rsp-${LSST_CONDA_ENV_NAME}"
# conda create --name ${rspname} --clone ${LSST_CONDA_ENV_NAME}

source ${LOADRSPSTACK}
mamba_ver=$(grep mamba versions/conda-stack.yml  | cut -d '=' -f 2)
conda install mamba=${mamba_ver}
ce=$(mamba env list | grep '\*' | awk '{print $1}') && \
    mamba env update -n ${ce} --file ${verdir}/conda-stack.yml && \
    mamba clean -a -y
# Install pyjs9 (not packaged on PyPi)
pip install git+https://github.com/ericmandel/pyjs9.git@${js9_ver}
# Add stack kernel
python3 -m ipykernel install --name 'LSST'
# Remove "system" kernel
stacktop="/opt/lsst/software/stack/conda/current"
rm -rf ${stacktop}/envs/${LSST_CONDA_ENV_NAME}/share/jupyter/kernels/python3
mamba clean -a -y
rm -rf /root/.cache/pip
