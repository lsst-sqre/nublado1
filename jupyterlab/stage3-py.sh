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
      'jupyterlab>=3,<4' \
      ipykernel \
      jupyterhub \
      jupyter-server-proxy \
      jupyter-packaging \
      geoviews \
      cookiecutter \
      nbval \
      pyshp \
      pypandoc \
      astroquery \
      ipywidgets \
      ipyevents \
      bokeh \
      cloudpickle \
      fastparquet \
      paramnb \
      ginga \
      bqplot \
      ipyvolume \
      papermill \
      dask \
      gcsfs \
      snappy \
      distributed \
      dask-kubernetes \
      "holoviews[recommended]" \
      datashader \
      python-snappy \
      graphviz \
      mysqlclient \
      hvplot \
      intake \
      intake-parquet \
      toolz \
      partd \
      nbdime \
      dask_labextension \
      numba \
      awkward \
      awkward-numba \
      pyvo \
      jupyterlab_iframe \
      jupyterlab_widgets \
      astrowidgets \
      sidecar \
      python-socketio \
      freetype-py \
      terminado \
      nodejs \
      yarn \
      jedi \
      xarray \
      jupyter_bokeh \
      pyviz_comms \
      pythreejs \
      bqplot \
      jupyterlab_execute_time \
      ipympl
# These are the things that are not in conda.
pip install --upgrade \
       nbconvert[webpdf] \
       wfdispatcher \
       socketIO-client \
       nclib \
       jupyterlab_hdf \
       lsst-efd-client \
       jupyter_firefly_extensions \
       lsst-rsp \
       rsp-jupyter-extensions
# wfdispatcher needs rework for JL3/nublado2

# Add stack kernel
python3 -m ipykernel install --name 'LSST'

# Remove "system" kernel
stacktop="/opt/lsst/software/stack/conda/current"
rm -rf ${stacktop}/envs/${LSST_CONDA_ENV_NAME}/share/jupyter/kernels/python3

# Clear Conda and pip caches
mamba clean -a -y
rm -rf /root/.cache/pip
