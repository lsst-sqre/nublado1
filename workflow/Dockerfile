FROM centos:8
USER root
RUN  yum install -y epel-release
RUN  yum -y upgrade
RUN  yum install -y python3 python3-devel git jq
RUN  python3 -m ensurepip
RUN  pip3 install --upgrade pip setuptools
#ENV  PYCURL_SSL_LIBRARY=openssl
RUN  pip3 install \
      wsgiserver \
      falcon \
      python-jose[cryptography] \
      mock \
      inflection \
      'jupyterhubutils>=0.15.4,<1.0.0' \
      'wfdispatcher>=0.0.7,<1.0.0'
#Uncomment this and add a git+https URL on a pip install below it when doing
# rapid test iteration.  Substitute date before rebuild.
# Something like:
# sed -i .bak -e "s/BUILDTRIGGER=\".*\"/BUILDTRIGGER=\"$(date)\"/" \
#  Dockerfile && dedangle && ./bld
#ARG  TKT="tickets/DM-23510"
#ARG  BUILDTRIGGER="Tue Feb 25 11:41:26 MST 2020"
#RUN  pip3 install --upgrade \
#      git+https://github.com/lsst-sqre/jupyterhubutils.git@${TKT} \
#      git+https://github.com/lsst-sqre/wfdispatcher.git@${TKT}
ENV  wf=/opt/lsst/software/workflow
ENV  verdir=${wf}/versions
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
       version="0.0.6"
CMD [ "/usr/local/bin/start-wf-api" ]
