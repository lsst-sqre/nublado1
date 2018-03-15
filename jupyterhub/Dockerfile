FROM centos:7
USER root
RUN  yum install -y epel-release
RUN  yum repolist
RUN  yum -y  upgrade
RUN  yum install -y python36 python-pip python36-pip nodejs python36-devel \
       libcurl-devel gcc net-tools sudo git patch
# There's no EPEL pip-3.6
# And EPEL doesn't do this either
RUN  ln -sf /usr/bin/python3.6 /usr/bin/python3
RUN  python3.6 -m ensurepip --default-pip
RUN  pip3 install --upgrade pip setuptools
RUN  npm install -g configurable-http-proxy
RUN  pip3 install jupyterlab ipykernel pyyaml pycurl python-oauth2 wheel \
      cryptography
RUN  pip3 install \
      https://github.com/jupyterhub/jupyterhub/zipball/master \
      https://github.com/jupyterhub/kubespawner/zipball/master \
      https://github.com/jupyterhub/oauthenticator/zipball/master
RUN  python3 /usr/local/bin/jupyter serverextension enable --py \
      jupyterlab --sys-prefix
RUN  mkdir -p /opt/lsst/software/jupyterhub/config
COPY hublauncher.sh /opt/lsst/software/jupyterhub/
# jupyterhub_config.py is stored in a ConfigMap
ENV  LANG=C.UTF-8
RUN  groupadd -g 768 jupyter
RUN  useradd -m -g jupyter -u 768 -c "JupyterHub User" jupyter
LABEL      description="jupyterlab demo: jupyterhub" \
             name="lsstsqre/jld-hub" \
	     version="0.5.0"
CMD [ "/opt/lsst/software/jupyterhub/hublauncher.sh" ]
