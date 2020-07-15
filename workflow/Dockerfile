FROM centos:8
USER root
RUN  yum install -y epel-release
RUN  yum -y upgrade
RUN  yum install -y python3 python3-devel jq git
RUN  python3 -m ensurepip
RUN  pip3 install --upgrade pip setuptools
#ENV  PYCURL_SSL_LIBRARY=openssl
RUN  pip3 install \
      wsgiserver \
      falcon \
      mock \
      inflection \
      kubernetes \
      'jupyterhubutils>=0.24.1,<1.0.0' \
      'wfdispatcher>=0.3.0,<1.0.0'
#Uncomment this and add a git+https URL on a pip install below it when doing
# rapid test iteration.  Substitute date before rebuild.
# Something like:
# sed -i .bak -e "s/BUILDTRIGGER=\".*\"/BUILDTRIGGER=\"$(date)\"/" \
#  Dockerfile && dedangle && ./bld
# ARG  TKT="tickets/DM-25827"
# ARG  BUILDTRIGGER="Tue Jul 14 15:34:31 MST 2020"
# RUN  pip3 install --upgrade \
#       git+https://github.com/lsst-sqre/wfdispatcher.git@${TKT}
#RUN  pip3 install --upgrade \
#      git+https://github.com/lsst-sqre/jupyterhubutils.git@${TKT}
ARG  wf=/opt/lsst/software/workflow
ARG  verdir=${wf}/versions
RUN  mkdir -p ${verdir}
RUN  mkdir ${wf}/config ${wf}/templates
RUN  pip3 freeze > ${verdir}/requirements.txt && \
      rpm -qa | sort > ${verdir}/rpmlist.txt
COPY start-wf-api /usr/local/bin
ENV  LANG=C.UTF-8
RUN  groupadd -g 768 jovyan
RUN  useradd -m -g jovyan -u 768 -c "JupyterHub User" jovyan
USER 768:768
LABEL description="Science Platform Notebook Aspect: workflow dispatcher" \
       name="lsstsqre/wfdispatcher" \
       version="0.3.0.0"
CMD [ "/usr/local/bin/start-wf-api" ]
