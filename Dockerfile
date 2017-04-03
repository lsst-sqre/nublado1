FROM       centos:7
MAINTAINER sqre-admin
LABEL      description="jupyterlab demo" \
           name="lsstsqre/jupyterlabdemo" \
           version="0.0.3"

USER       root
RUN        yum install -y epel-release
RUN        yum repolist
RUN        yum install -y python34
RUN        yum install -y python34-pip python34-devel gcc nodejs \
             python-pip python-devel python-virtualenvwrapper which
RUN        pip3 install --upgrade pip setuptools six virtualenv
RUN        pip2 install --upgrade pip setuptools six virtualenv
RUN        useradd -d /home/jupyterlab -m jupyterlab
USER       jupyterlab
ENV        LANG=C.UTF-8
WORKDIR    /home/jupyterlab
RUN        mkdir -p /home/jupyterlab/data
RUN        /bin/bash -c "source /usr/bin/virtualenvwrapper.sh \
           && mkvirtualenv jupyterlab2 \
           && pip install --upgrade pip \
           && pip install --upgrade setuptools six \
           && pip install jupyterlab ipykernel \
           && jupyter serverextension enable --py jupyterlab --sys-prefix"
RUN        /bin/bash -c "source /usr/bin/virtualenvwrapper.sh \
           && mkvirtualenv -p $(which python3) jupyterlab \
           && pip3 install --upgrade pip \
           && pip3 install --upgrade setuptools six \
           && pip3 install jupyterlab ipykernel \
           && jupyter serverextension enable --py jupyterlab --sys-prefix \
	   && /home/jupyterlab/.virtualenvs/jupyterlab2/bin/python -m \
	      ipykernel install --prefix \
              /home/jupyterlab/.virtualenvs/jupyterlab --name 'Python2'"
COPY       ./run-jupyterlab.bash .
EXPOSE     8888
CMD        [ "./run-jupyterlab.bash" ]

