#!/bin/sh
set -e
#This commented-out bit, plus changing the definition of LOADRSPSTACK in
# Dockerfile.template, will clone the environment rather than installing
# into the stack environment itself.  This adds 60% or so to the container
# size.
#
# source ${LOADSTACK}
# rspname="rsp-${LSST_CONDA_ENV_NAME}"
# conda create --name ${rspname} --clone ${LSST_CONDA_ENV_NAME}
#
source ${LOADRSPSTACK}
conda install -y mamba # not strictly necessary, but better error reporting
mamba install --no-banner -y \
      'jupyterlab>=2.3.1,<3' \
      'ipykernel<6' \
      jupyterhub \
      jupyter-server-proxy \
      jupyter-packaging \
      geoviews \
      cookiecutter \
      nbval \
      pyshp \
      pypandoc \
      astroquery \
      ipyevents \
      ipywidgets \
      ipyevents \
      bokeh \
      cloudpickle \
      ipympl \
      fastparquet \
      paramnb \
      ginga \
      bqplot \
      ipyvolume \
      papermill \
      'dask=2020.12' \
      gcsfs \
      snappy \
      'distributed=2020.12' \
      'dask-kubernetes=0.11.0' \
      "holoviews[recommended]" \
      datashader \
      python-snappy \
      graphviz \
      'mysqlclient!=2.0.2' \
      hvplot \
      intake \
      intake-parquet \
      jupyter-server-proxy \
      toolz \
      partd \
      nbdime \
      dask_labextension \
      numba \
      awkward \
      awkward-numba \
      pyvo \
      'jupyterlab_iframe<0.3' \
      astrowidgets \
      sidecar \
      python-socketio \
      pywwt \
      freetype-py \
      terminado \
      nodejs \
      yarn \
      jedi \
      xarray
# These are the things that are not in conda.
pip install --upgrade \
       'lsst-efd-client==0.8.3' \
       wfdispatcher \
       socketIO-client \
       jupyterlab_hdf \
       jupyter_firefly_extensions \
       nbconvert[webpdf] \
       nclib \
       rubin_jupyter_utils.lab \
       git+https://github.com/ericmandel/pyjs9

# Add stack kernel
python3 -m ipykernel install --name 'LSST'

# Remove "system" kernel
stacktop="/opt/lsst/software/stack/conda/current"
rm -rf ${stacktop}/envs/${LSST_CONDA_ENV_NAME}/share/jupyter/kernels/python3

# Clear Conda and pip caches
mamba clean -a -y
rm -rf /root/.cache/pip
