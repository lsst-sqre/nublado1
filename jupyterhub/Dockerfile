FROM centos:7
USER root
LABEL      description="jupyterlab demo: jupyterhub" \
             name="lsstsqre/jld-hub" \
             version="0.0.2"
RUN  yum install -y epel-release
RUN  yum repolist
RUN  yum -y upgrade
RUN  yum install -y python34 python-pip python34-pip nodejs python34-devel \
       libcurl-devel gcc net-tools
RUN  pip3 install --upgrade pip
RUN  npm install -g configurable-http-proxy
RUN  pip3 install jupyterlab ipykernel pyyaml pycurl \
     'sqre_ghowlauth>=0.0.6' 'sqrekubespawner>=0.0.3'
# We need JupyterHub 0.8.0, and it is not on PyPi yet (4/24/2017)...
# So build it locally, then cram the wheel into the assets subdir.
COPY assets/jupyterhub-0.8.0.dev0-py3-none-any.whl \
     /tmp/
RUN  pip3 install /tmp/jupyterhub-0.8.0.dev0-py3-none-any.whl
RUN  rm /tmp/jupyterhub-0.8.0.dev0-py3-none-any.whl
RUN  python3 /usr/bin/jupyter serverextension enable --py jupyterlab --sys-prefix
RUN  mkdir -p /opt/lsst/software/jupyterhub/
COPY jupyterhub_config.py hublauncher.sh /opt/lsst/software/jupyterhub/
ENV  LANG=C.UTF-8
CMD [ "/opt/lsst/software/jupyterhub/hublauncher.sh" ]

