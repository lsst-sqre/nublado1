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
RUN  mkdir -p /usr/share/git && \
     cd /usr/share/git && \
     git clone https://github.com/jupyterhub/jupyterhub.git && \
     cd jupyterhub && \
     git rev-parse HEAD > /root/jupyterhub.commit && \
     python3 setup.py bdist_wheel && \
     cd dist && \
     whl=$(ls *.whl) && \
     pip3 install ${whl}
RUN pip3 install \
     https://github.com/lsst-sqre/oauthenticator/zipball/master \
     https://github.com/jupyterhub/kubespawner/zipball/master
RUN  python3 /usr/bin/jupyter serverextension enable --py \
      jupyterlab --sys-prefix
RUN  mkdir -p /opt/lsst/software/jupyterhub/config
COPY hublauncher.sh /opt/lsst/software/jupyterhub/
# jupyterhub_config.py is stored in a ConfigMap
ENV  LANG=C.UTF-8
RUN  groupadd -g 768 jupyter
RUN  useradd -m -g jupyter -u 768 -c "JupyterHub User" jupyter
LABEL      description="jupyterlab demo: jupyterhub" \
             name="lsstsqre/jld-hub" \
	     version="0.4.1"
CMD [ "/opt/lsst/software/jupyterhub/hublauncher.sh" ]
