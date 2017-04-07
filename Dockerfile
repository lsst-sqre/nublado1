FROM lsstsqre/centos:7-stack-lsst_distrib-v13_0
MAINTAINER sqre-admin
LABEL      description="jupyterlab demo" \
           name="lsstsqre/jupyterlabdemo" \
           version="0.0.7C"
USER root
RUN  yum install -y epel-release
RUN  yum repolist
RUN  yum install -y python34 python-pip python34-pip nodejs
RUN  pip3 install --upgrade pip
RUN  pip2 install --upgrade pip
RUN  pip3 install virtualenv virtualenvwrapper
RUN  pip2 install virtualenv virtualenvwrapper
RUN  npm install -g configurable-http-proxy
RUN  source /opt/lsst/software/stack/loadLSST.bash && \
     pip install ipykernel jupyterlab
USER vagrant
COPY jupyterhub_config.py .
RUN  . virtualenvwrapper.sh && \
     mkvirtualenv -p $(which python3) py3 && \
     pip install jupyterhub jupyterlab jupyterhub-dummyauthenticator && \
     /opt/lsst/software/stack/Linux64/miniconda2/4.2.12.lsst1/bin/python \
      -m ipykernel install --prefix $HOME/.virtualenvs/py3 --name 'LSST_Stack'
RUN  mkdir ./data
CMD  [ "/bin/bash", "--login" ]
