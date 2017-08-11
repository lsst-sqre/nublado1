FROM centos:7
USER root
RUN  yum install -y epel-release
RUN  yum repolist
RUN  yum -y upgrade
RUN  yum install -y python34 python-pip python34-pip nodejs python34-devel \
       libcurl-devel gcc net-tools sudo git patch
RUN  pip3 install --upgrade pip setuptools
RUN  npm install -g configurable-http-proxy
RUN  pip3 install jupyterlab ipykernel pyyaml pycurl python-oauth2 wheel \
       cryptography
# RUN  pip3 install https://github.com/jupyterhub/jupyterhub/zipball/master
#  does not work, because it doesn't rebuild the JS
# 184a9bceb9069ae60f86eddedba279552b1bc2e8 is stable for tutorial.  Catch up
#  later.
RUN  mkdir -p /usr/share/git && \
     cd /usr/share/git && \
     git clone https://github.com/jupyterhub/jupyterhub.git  && \
     cd jupyterhub && \
     git checkout 184a9bceb9069ae60f86eddedba279552b1bc2e8 && \
     git rev-parse HEAD > /root/jupyterhub.commit && \
     python3 setup.py bdist_wheel  && \
     pip3 install dist/jupyterhub-0.8.0.dev0-py3-none-any.whl
#     https://github.com/lsst-sqre/oauthenticator/zipball/tickets/DM-11417  \
# 09b2a5323bda0d9a81a53a644c4b699b1e156087
# More recent ones are having issues with the redirect.
#      https://github.com/lsst-sqre/oauthenticator/zipball/09b2a5323bda0d9a81a53a644c4b699b1e156087 \
#     https://github.com/lsst-sqre/oauthenticator/zipball/tickets/DM-11417  \
RUN pip3 install \
     https://github.com/lsst-sqre/oauthenticator/zipball/tickets/DM-11557  \
     https://github.com/jupyterhub/kubespawner/zipball/master
RUN  python3 /usr/bin/jupyter serverextension enable --py \
      jupyterlab --sys-prefix
RUN  mkdir -p /opt/lsst/software/jupyterhub/config
COPY hublauncher.sh /opt/lsst/software/jupyterhub/
#COPY auth.py.patch /opt/lsst/software/jupyterhub
#RUN  cd /usr/lib/python3.4/site-packages/jupyterhub/apihandlers && \
#     patch < /opt/lsst/software/jupyterhub/auth.py.patch
# jupyterhub_config.py is stored in a ConfigMap
ENV  LANG=C.UTF-8
RUN  groupadd -g 768 jupyter
RUN  useradd -m -g jupyter -u 768 -c "JupyterHub User" jupyter
LABEL      description="jupyterlab demo: jupyterhub" \
             name="lsstsqre/jld-hub" \
	     version="0.2.1"
CMD [ "/opt/lsst/software/jupyterhub/hublauncher.sh" ]
