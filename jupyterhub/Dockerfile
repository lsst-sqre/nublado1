FROM centos:7
USER root
RUN  yum install -y epel-release
RUN  yum repolist
RUN  yum -y upgrade
RUN  yum install -y nodejs libcurl-devel mysql-devel gcc net-tools sudo \
      git patch python-alembic mariadb mysql python36 python36-devel
RUN  alternatives --install /usr/bin/python3 python3 /usr/bin/python36 50 && \
      python3 -m ensurepip
RUN  pip3 install --upgrade pip setuptools
ENV  PYCURL_SSL_LIBRARY=openssl
# Need master versions of authenticators and hub
#  Pin oauthenticator: shift from tornado to native async hurt.
RUN  pip3 install \
      tornado \
      ipykernel \
      pyyaml \
      pycurl \
      python-oauth2 \
      wheel \
      cryptography \
      mysqlclient \
      jupyterhub-kubespawner \
      'kubernetes>=9.0.0,<10.0.0' \
      'requests>=2.0.0,<3.0.0' \
      'jupyterhubutils>=0.5.3' \
      'namespacedkubespawner>=0.0.19' \
      jupyterlab \
      jupyterhub \
      git+https://github.com/mogthesprog/jwtauthenticator.git \
      git+https://github.com/jupyterhub/oauthenticator.git@04d664e559275c0c705f1882ce1307cc47227594
RUN  jupyter serverextension enable --py jupyterlab --sys-prefix
ENV  jh=/opt/lsst/software/jupyterhub
ENV  verdir=${jh}/versions
RUN  mkdir -p ${verdir}
RUN  mkdir ${jh}/config ${jh}/templates
RUN  pip3 freeze > ${verdir}/requirements.txt && \
      rpm -qa | sort > ${verdir}/rpmlist.txt
COPY hublauncher.sh /opt/lsst/software/jupyterhub/
COPY title.html /opt/lsst/software/jupyterhub/templates/
# The template override is not working.  Here is a nasty hack to get
#  the same effect.
RUN  sed -i -e \
    's/ %}JupyterHub{% / %}LSST Science Platform Interactive Environment{% /' \
     /usr/local/share/jupyterhub/templates/page.html
# jupyterhub_config.py is stored in a ConfigMap
ENV  LANG=C.UTF-8
RUN  groupadd -g 768 jovyan
RUN  useradd -m -g jovyan -u 768 -c "JupyterHub User" jovyan
# This must be numeric for k8s non-root contexts
USER 768:768
LABEL description="Science Platform Notebook Aspect: jupyterhub" \
       name="lsstsqre/sciplat-hub" \
       version="exp_0.15.6"
CMD [ "/opt/lsst/software/jupyterhub/hublauncher.sh" ]
