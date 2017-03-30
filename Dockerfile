FROM       centos:7
MAINTAINER sqre-admin
LABEL      description="jupyterlab demo" \
           name="lsstsqre/jupyterlabdemo" \
           version="0.0.1"

USER       root
RUN        yum install -y epel-release
RUN        yum repolist
RUN        yum install -y python-pip python-devel gcc nodejs \
             python-virtualenvwrapper which
RUN        pip install --upgrade pip setuptools six	     
RUN        useradd -d /home/jupyterlab -m jupyterlab
USER       jupyterlab
ENV        LANG=C.UTF-8
WORKDIR    /home/jupyterlab
RUN        /bin/bash -c "source /usr/bin/virtualenvwrapper.sh \
           && mkvirtualenv jupyterlab \
           && pip install --upgrade pip \
           && pip install --upgrade setuptools six \
           && pip install jupyterlab \
           && jupyter serverextension enable --py jupyterlab --sys-prefix"
RUN        mkdir -p /home/jupyterlab/data
COPY       run-jupyter.bash .
EXPOSE     8888
CMD        [ "./run-jupyter.bash" ]
