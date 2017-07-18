FROM centos:7
USER root
LABEL      description="jupyterlab demo: jupyterhub" \
             name="lsstsqre/jld-hub" \
             version="0.1.3"
RUN  yum install -y epel-release
RUN  yum repolist
RUN  yum -y upgrade
RUN  yum install -y python34 python-pip python34-pip nodejs python34-devel \
       libcurl-devel gcc net-tools sudo git patch
RUN  pip3 install --upgrade pip setuptools
RUN  npm install -g configurable-http-proxy
RUN  pip3 install jupyterlab ipykernel pyyaml pycurl python-oauth2 wheel \
      sqrekubespawner \
      sqre_ghowlauth
# RUN  pip3 install https://github.com/jupyterhub/jupyterhub/zipball/master
#  does not work, because it doesn't rebuild the JS
RUN  mkdir -p /usr/share/git && \
     cd /usr/share/git && \
     git clone https://github.com/jupyterhub/jupyterhub.git && \
     cd jupyterhub && \
     python3 setup.py bdist_wheel && \
     pip3 install dist/jupyterhub-0.8.0.dev0-py3-none-any.whl
RUN  python3 /usr/bin/jupyter serverextension enable --py \
      jupyterlab --sys-prefix
RUN  mkdir -p /opt/lsst/software/jupyterhub/config
# Patch handlers/base.py to be OK with "name" being a dict:
COPY hublauncher.sh base.py.patch /opt/lsst/software/jupyterhub/
RUN cd /usr/lib/python3.4/site-packages/jupyterhub/handlers && \
    patch < /opt/lsst/software/jupyterhub/base.py.patch
# jupyterhub_config.py is stored in a ConfigMap
ENV  LANG=C.UTF-8
RUN  groupadd -g 768 jupyter
RUN  useradd -m -g jupyter -u 768 -c "JupyterHub User" jupyter
CMD [ "/opt/lsst/software/jupyterhub/hublauncher.sh" ]
