FROM centos:7
USER root
RUN  yum install -y epel-release
RUN  yum repolist
RUN  yum -y upgrade
RUN  yum install -y python3 git
RUN  python3 -m ensurepip
RUN  pip3 install --upgrade pip setuptools wheel
RUN  pip3 install \
      'rubin_jupyter_utils.hub>=0.37.2,<1.0'
#Uncomment this and add a git+https URL on a pip install below it when doing
# rapid test iteration.  Substitute date before rebuild.
# Something like:
# sed -i .bak -e "s/BUILDTRIGGER=\".*\"/BUILDTRIGGER=\"$(date)\"/" \
#  Dockerfile && dedangle && ./bld
#ARG  TKT="tickets/DM-28302"
#ARG  BUILDTRIGGER="Sun Nov  1 18:58:39 MST 2020"
#RUN  pip3 install --upgrade \
#      git+https://github.com/lsst-sqre/rubin-jupyter-helpers.git@${TKT} \
#      git+https://github.com/lsst-sqre/rubin-jupyter-hub.git@${TKT} \
#      git+https://github.com/lsst-sqre/rubin-jupyter-config.git@${TKT}
ENV  LANG=C.UTF-8
RUN  groupadd -g 768 jovyan
RUN  useradd -m -g jovyan -u 768 -c "JupyterHub User" jovyan
# This must be numeric for k8s non-root contexts
USER 768:768
CMD [ "/usr/local/bin/prepuller" ]
LABEL      description="nublado: image prepuller" \
             name="lsstsqre/prepuller" \
             version="0.10.1-pre0"
