FROM centos:7
USER root
ENV  epel_release="epel-release-7-11.noarch"
ENV  jh=/opt/lsst/software/jupyterhub
ENV  verdir=${jh}/versions
RUN  mkdir -p ${verdir}
COPY versions/* ${verdir}/
RUN  yum install -y ${epel_release}
RUN  yum repolist && yum updateinfo
RUN  yum -y install $(cat ${verdir}/rpmlist.txt | xargs)
# Make EPEL Python 3.6 system Python 3 and install pip3
RUN  alternatives --install /usr/bin/python3 python3 \
      /usr/bin/python36 50 && \
      python3 -m ensurepip
ENV  PYCURL_SSL_LIBRARY=openssl
# Need not-yet-released jwtauthenticator
# Tornado needs to be version < 6.0
RUN  pip3 install --upgrade -r ${verdir}/requirements.txt
RUN  pycurl_ver="$(grep pycurl ${verdir}/requirements.txt | \
        cut -d '=' -f 3- )" && \
     pip3 uninstall -y pycurl && \
     export PYCURL_SSL_LIBRARY=nss && \
     pip3 install --compile --install-option="--with-nss" --no-cache-dir \
      "pycurl==${pycurl_ver}"
RUN  jwtver=$(cat ${verdir}/jwtauthenticator.commit) && \
      pip3 install --upgrade \
       git+https://github.com/mogthesprog/jwtauthenticator.git@${jwtver}
RUN jupyter serverextension enable --py jupyterlab --sys-prefix
RUN  mkdir ${jh}/config ${jh}/templates
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
       version="exp_0.16.3"
CMD [ "/opt/lsst/software/jupyterhub/hublauncher.sh" ]
