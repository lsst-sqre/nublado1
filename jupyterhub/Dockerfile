FROM centos:7
USER root
RUN  yum install -y epel-release
RUN  yum repolist && yum updateinfo
RUN  yum -y upgrade
RUN  yum install -y nodejs libcurl-devel mysql-devel gcc net-tools sudo \
      git patch python-alembic mariadb mysql python3 python3-devel
RUN  python3 -m ensurepip
RUN  pip3 install --upgrade pip setuptools
ENV  PYCURL_SSL_LIBRARY=openssl
RUN  pip3 install \
      tornado \
      ipykernel \
      pyyaml \
      python-oauth2 \
      wheel \
      cryptography \
      mysqlclient \
      jupyterhub-kubespawner \
      'kubernetes>=9.0.0,<10.0.0' \
      'requests>=2.0.0,<3.0.0' \
      jupyterlab \
      oauthenticator \
      namespacedkubespawner \
      semver \
      git+https://github.com/jupyterhub/jupyterhub \
      git+https://github.com/mogthesprog/jwtauthenticator.git
RUN  pip uninstall pycurl && \
      export PYCURL_SSL_LIBRARY=nss && \
      pip install --compile --install-option="--with-nss" --no-cache-dir pycurl
#Remove this and move the pip install back up when we are done
ARG  BUILDTRIGGER="Sat Dec 14 17:23:43 MST 2019"
RUN  pip install git+https://github.com/lsst-sqre/jupyterhubutils.git@tickets/DM-22011B
RUN  jupyter serverextension enable --py jupyterlab --sys-prefix
ENV  jh=/opt/lsst/software/jupyterhub
ENV  verdir=${jh}/versions
RUN  mkdir -p ${verdir}
RUN  mkdir ${jh}/config ${jh}/templates
RUN  pip3 freeze > ${verdir}/requirements.txt && \
      rpm -qa | sort > ${verdir}/rpmlist.txt
COPY hublauncher.sh /opt/lsst/software/jupyterhub/
COPY title.html options_form.template.html \
      /opt/lsst/software/jupyterhub/templates/
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
       version="exp_0.16.10.1"
CMD [ "/opt/lsst/software/jupyterhub/hublauncher.sh" ]
