FROM centos:7
USER root
RUN  yum install -y epel-release
RUN  yum repolist
RUN  yum -y  upgrade
RUN  yum install -y nodejs libcurl-devel mysql-devel gcc net-tools sudo \
      git patch python-alembic
# Python 3.6: install from SCL
RUN  yum -y install centos-release-scl && \
     yum-config-manager --enable rhel-server-rhscl-7-rpms && \
     yum -y install rh-python36
RUN  source scl_source enable rh-python36 && \
      pip3 install --upgrade pip setuptools
RUN  npm install -g configurable-http-proxy
RUN  source scl_source enable rh-python36 && \
     pip3 install jupyterlab ipykernel pyyaml pycurl python-oauth2 wheel \
      cryptography mysqlclient
RUN  source scl_source enable rh-python36 && \
      pip3 install \
       https://github.com/jupyterhub/jupyterhub/zipball/master \
       https://github.com/jupyterhub/kubespawner/zipball/master \
       https://github.com/jupyterhub/oauthenticator/zipball/master \
       https://github.com/lsst-sqre/jupyterutils/zipball/master
RUN  source scl_source enable rh-python36 && \
      jupyter serverextension enable --py \
      jupyterlab --sys-prefix
RUN  mkdir -p /opt/lsst/software/jupyterhub/config
RUN  mkdir /opt/lsst/software/jupyterhub/templates
COPY hublauncher.sh hubwrapper.sh /opt/lsst/software/jupyterhub/
COPY title.html /opt/lsst/software/jupyterhub/templates/
COPY local01-scl.sh /etc/profile.d/
# The template override is not working.  Here is a nasty hack to get
#  the same effect.
RUN  sed -i -e \
    's/ %}JupyterHub{% / %}LSST Science Platform Interactive Environment{% /' \
     /opt/rh/rh-python36/root/usr/share/jupyterhub/templates/page.html
# jupyterhub_config.py is stored in a ConfigMap
ENV  LANG=C.UTF-8
RUN  groupadd -g 768 jupyter
RUN  useradd -m -g jupyter -u 768 -c "JupyterHub User" jupyter
LABEL      description="jupyterlab demo: jupyterhub" \
             name="lsstsqre/jld-hub" \
	     version="0.7.8"
CMD [ "/opt/lsst/software/jupyterhub/hublauncher.sh" ]
