FROM centos:7
USER root
RUN  yum install -y epel-release
RUN  yum repolist
RUN  yum -y  upgrade
RUN  yum install -y nodejs libcurl-devel mysql-devel gcc net-tools sudo \
      git patch python-alembic mariadb mysql python36 python36-devel
# Python 3.6: install from EPEL
RUN  alternatives --install /usr/bin/python3 python3 /usr/bin/python36 50 && \
      python3 -m ensurepip
RUN  pip3 install --upgrade pip setuptools
ENV  PYCURL_SSL_LIBRARY=openssl
# Use forked oauthenticator until PR lands.
RUN  pip3 install jupyterlab \
      ipykernel \
      pyyaml \
      pycurl \
      python-oauth2 \
      wheel \
      cryptography \
      mysqlclient \
      jupyterhub \
      jupyterhubutils \
      jupyterhub-kubespawner \
      namespacedkubespawner \
      git+https://github.com/mogthesprog/jwtauthenticator.git \
      git+https://github.com/jupyterhub/oauthenticator.git
RUN jupyter serverextension enable --py jupyterlab --sys-prefix
RUN  mkdir -p /opt/lsst/software/jupyterhub/config
RUN  mkdir /opt/lsst/software/jupyterhub/templates
COPY hublauncher.sh /opt/lsst/software/jupyterhub/
COPY title.html /opt/lsst/software/jupyterhub/templates/
# The template override is not working.  Here is a nasty hack to get
#  the same effect.
RUN  sed -i -e \
    's/ %}JupyterHub{% / %}LSST Science Platform Interactive Environment{% /' \
     /usr/local/share/jupyterhub/templates/page.html
# jupyterhub_config.py is stored in a ConfigMap
ENV  LANG=C.UTF-8
RUN  groupadd -g 768 jupyter
RUN  useradd -m -g jupyter -u 768 -c "JupyterHub User" jupyter
LABEL      description="Science Platform Notebook Aspect: jupyterhub" \
             name="lsstsqre/sciplat-hub" \
	     version="0.12.0"
CMD [ "/opt/lsst/software/jupyterhub/hublauncher.sh" ]
