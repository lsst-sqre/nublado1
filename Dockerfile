FROM       centos:7
MAINTAINER sqre-admin
LABEL      description="jupyterlab demo" \
           name="lsstsqre/jupyterlabdemo" \
           version="0.0.6"
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
	   conda install python==3.5.2 && \
           conda create -n py2 python=2 && \
           source activate py2 && \
           conda install ipykernel && \
	   conda install -y -c conda-forge jupyterlab && \
	   conda config --add channels \
             http://conda.lsst.codes/stack/0.13.0 && \
	   conda install lsst-distrib && \
	   conda config --remove channels \
	     http://conda.lsst.codes/stack/0.13.0 && \
	   ipython kernel install && \
	   source deactivate py2 && \
	   conda create -n py3 python=3.5.2 && \
	   source activate py3 && \
           conda install ipykernel && \
	   ipython kernel install && \
           conda install -y -c conda-forge jupyterhub jupyterlab && \
	   conda config --add channels \
	     http://conda.lsst.codes/stack/0.13.0.rc1-py3 && \
	   conda install lsst-distrib && \
	   source eups-setups.sh && \
	   setup lsst_distrib && \
	   pip install jupyterhub-dummyauthenticator
COPY       ./pylaunch.sh /usr/local/bin/pylaunch.sh
COPY	   ./k3.json /usr/local/share/jupyter/kernels/python3/kernel.json
COPY	   ./k2.json /usr/local/share/jupyter/kernels/python2/kernel.json
RUN        useradd -d /home/jupyterlab -m jupyterlab
USER       jupyterlab
ENV        LANG=C.UTF-8
WORKDIR    /home/jupyterlab
COPY       ./jupyterhub_config.py .
COPY	   ./run-jupyterhub.bash .
RUN        mkdir -p /home/jupyterlab/data
EXPOSE     8000
CMD        [ "./run-jupyterhub.bash" ]
