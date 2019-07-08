FROM centos:7
USER root
RUN  yum install -y epel-release
RUN  yum repolist
RUN  yum -y upgrade
RUN  yum install -y python36 git
RUN  alternatives --install /usr/bin/python3 python3 /usr/bin/python36 \
       50 && \
      python3 -m ensurepip
RUN  pip3 install --upgrade pip setuptools
RUN  pip3 install 'jupyterhubutils>=0.5.6'
COPY prepull /usr/bin/prepull
RUN  chmod 0755 /usr/bin/prepull
ENV  LANG=C.UTF-8
RUN  groupadd -g 768 jovyan
RUN  useradd -m -g jovyan -u 768 -c "JupyterHub User" jovyan
# This must be numeric for k8s non-root contexts
USER 768:768
CMD [ "/usr/bin/prepull" ]
LABEL      description="nublado: image prepuller" \
             name="lsstsqre/prepuller" \
             version="0.4.1"
