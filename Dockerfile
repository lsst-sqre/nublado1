FROM       centos:7
MAINTAINER sqre-admin
LABEL      description="jupyterlab demo" \
           name="lsstsqre/jupyterlabdemo" \
           version="0.0.4"

USER       root
RUN        yum install -y epel-release
RUN        yum repolist
RUN        yum install -y python34
RUN        yum install -y python34-pip python34-devel gcc nodejs \
             python-pip python-devel python-virtualenvwrapper which
RUN        pip3 install --upgrade pip setuptools six virtualenv \
             virtualenvwrapper
RUN        pip2 install --upgrade pip setuptools six virtualenv \
             virtualenvwrapper
RUN        npm install -g configurable-http-proxy
RUN        useradd -d /home/jupyterlab -m jupyterlab
USER       jupyterlab
ENV        LANG=C.UTF-8
WORKDIR    /home/jupyterlab
COPY       ./jupyterhub_config.py .
COPY	   ./run-jupyterhub.bash .
RUN        mkdir -p /home/jupyterlab/data
RUN        /bin/bash -c "source /usr/bin/virtualenvwrapper.sh \
           && mkvirtualenv jupyterlab2 \
           && pip install --upgrade pip \
           && pip install --upgrade setuptools six virtualenvwrapper \
           && pip install jupyterlab ipykernel \
           && jupyter serverextension enable --py jupyterlab --sys-prefix"
RUN        /bin/bash -c "source /usr/bin/virtualenvwrapper.sh \
           && mkvirtualenv -p $(which python3) jupyterlab \
           && pip3 install --upgrade pip \
           && pip3 install --upgrade setuptools six virtualenvwrapper \
           && pip3 install jupyterlab ipykernel \
           && pip3 install jupyterhub jupyterhub-dummyauthenticator \
           && jupyter serverextension enable --py jupyterlab --sys-prefix \
	   && /home/jupyterlab/.virtualenvs/jupyterlab2/bin/python -m \
	      ipykernel install --prefix \
              /home/jupyterlab/.virtualenvs/jupyterlab --name 'Python2'"

EXPOSE     8000
CMD        [ "./run-jupyterhub.bash" ]
