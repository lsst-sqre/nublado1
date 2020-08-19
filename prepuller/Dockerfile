FROM centos:7
USER root
RUN  yum install -y epel-release
RUN  yum repolist
RUN  yum -y upgrade
RUN  yum install -y python3 git
RUN  python3 -m ensurepip
RUN  pip3 install --upgrade pip setuptools
RUN  pip3 install \
      'rubin_jupyter_utils.hub>=0.30.1,<1.0'
ENV  LANG=C.UTF-8
RUN  groupadd -g 768 jovyan
RUN  useradd -m -g jovyan -u 768 -c "JupyterHub User" jovyan
# This must be numeric for k8s non-root contexts
USER 768:768
CMD [ "/usr/local/bin/prepuller" ]
LABEL      description="nublado: image prepuller" \
             name="lsstsqre/prepuller" \
             version="exp_0.8.0"
