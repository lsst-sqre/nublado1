FROM       centos:7
MAINTAINER sqre-admin
LABEL      description="jupyterlab demo" \
           name="lsstsqre/jupyterlabdemo" \
           version="0.0.5C"
ENV	   CONDA_VER="https://repo.continuum.io/miniconda/Miniconda3-latest"
ENV        CONDA_ARCH="Linux-x86_64.sh"
USER       root
RUN        yum install -y epel-release
RUN        yum repolist
RUN        yum install -y nodejs bzip2 which
RUN        curl --limit-rate 9M "${CONDA_VER}-${CONDA_ARCH}" > a.sh && \
               /bin/bash a.sh -p /opt/conda -b && \
               rm a.sh 
RUN        export PATH=/opt/conda/bin:$PATH && \
           conda create -n py2 python=2 && \
           source activate py2 && \
           conda install ipykernel && \
	   ipython kernel install && \
	   source deactivate py2 && \
	   conda create -n py3 python=3 && \
	   source activate py3 && \
           conda install ipykernel && \
	   ipython kernel install && \
	   source deactivate py3 && \
           conda install -y -c conda-forge jupyterhub jupyterlab && \
	   pip install jupyterhub-dummyauthenticator
RUN        useradd -d /home/jupyterlab -m jupyterlab
USER       jupyterlab
ENV        LANG=C.UTF-8
WORKDIR    /home/jupyterlab
COPY       ./jupyterhub_config.py .
COPY	   ./run-jupyterhub.bash .
RUN        mkdir -p /home/jupyterlab/data
EXPOSE     8000
CMD        [ "./run-jupyterhub.bash" ]
