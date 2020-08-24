FROM centos:7
USER root
RUN  yum install -y epel-release
RUN  yum repolist && yum updateinfo
RUN  yum -y upgrade
RUN  yum install -y nodejs libcurl-devel mysql-devel gcc net-tools sudo \
      patch git python-alembic mariadb mysql python3 python3-devel postgresql
RUN  python3 -m ensurepip
RUN  pip3 install --upgrade setuptools pip
ENV  PYCURL_SSL_LIBRARY=openssl
RUN  pip3 install \
      tornado \
      ipykernel \
      python-oauth2 \
      wheel \
      cryptography \
      mysqlclient \
      psycopg2-binary \
      jupyterhub-kubespawner \
      'kubernetes>=11' \
      'requests>=2,<3' \
      jupyterlab \
      semver \
      oauthenticator \
      jupyterhub \
      pyyaml \
      'rubin_jupyter_utils.hub>=0.30.2,<1'
RUN  pip uninstall pycurl && \
      export PYCURL_SSL_LIBRARY=nss && \
      pip install --compile --install-option="--with-nss" --no-cache-dir \
       pycurl
#Uncomment this and add a git+https URL on a pip install below it when doing
# rapid test iteration.  Substitute date before rebuild.
# Something like:
# sed -i .bak -e "s/BUILDTRIGGER=\".*\"/BUILDTRIGGER=\"$(date)\"/" \
#  Dockerfile && dedangle && ./bld
# ARG  BUILDTRIGGER="Mon Aug  3 17:47:14 MST 2020"
# ARG  TKT="tickets/DM-26118"
# RUN  pip3 install --upgrade \
#      git+https://github.com/lsst-sqre/jupyterhubutils.git@${TKT}
RUN  jupyter serverextension enable --py jupyterlab --sys-prefix
ENV  jh=/opt/lsst/software/jupyterhub
ENV  verdir=${jh}/versions
RUN  mkdir -p ${verdir}
RUN  mkdir ${jh}/config ${jh}/templates
RUN  pip3 freeze > ${verdir}/requirements.txt && \
      rpm -qa | sort > ${verdir}/rpmlist.txt
COPY hublauncher.sh /opt/lsst/software/jupyterhub/
COPY page.html options_form.template.html \
      /opt/lsst/software/jupyterhub/templates/
# jupyterhub_config.py is stored in a ConfigMap
ENV  LANG=C.UTF-8
RUN  groupadd -g 768 jovyan
RUN  useradd -m -g jovyan -u 768 -c "JupyterHub User" jovyan
# This must be numeric for k8s non-root contexts
USER 768:768
LABEL description="Science Platform Notebook Aspect: jupyterhub" \
       name="lsstsqre/sciplat-hub" \
       version="0.30.2"
CMD [ "/opt/lsst/software/jupyterhub/hublauncher.sh" ]
