FROM centos:8
USER root
RUN  yum install -y epel-release
RUN  yum -y upgrade
RUN  yum install -y python3 python3-devel jq git
RUN  python3 -m ensurepip
RUN  pip3 install --upgrade pip setuptools wheel
RUN  pip3 install \
      wsgiserver \
      mock \
      falcon \
      inflection \
      kubernetes \
      "wfdispatcher>=0.4.2,<1.0"
#Uncomment this and add a git+https URL on a pip install below it when doing
# rapid test iteration.  Substitute date before rebuild.
# Something like:
# sed -i .bak -e "s/BUILDTRIGGER=\".*\"/BUILDTRIGGER=\"$(date)\"/" \
#  Dockerfile && dedangle && ./bld
#ARG  TKT="tickets/DM-26311"
#ARG  BUILDTRIGGER="Thu Aug 20 15:35:51 MST 2020"
#RUN  pip3 install --upgrade \
#      git+https://github.com/lsst-sqre/wfdispatcher.git@${TKT}
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
       version="0.4.3-pre0"
CMD [ "/usr/local/bin/start-wf-api" ]
