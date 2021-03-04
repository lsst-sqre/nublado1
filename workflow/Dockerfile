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
      kubernetes \
      inflection \
      "wfdispatcher>=0.4.2,<1.0"
#Uncomment this and add a git+https URL on a pip install below it when doing
# rapid test iteration.  Substitute date before rebuild.
# Something like:
# sed -i .bak -e "s/BUILDTRIGGER=\".*\"/BUILDTRIGGER=\"$(date)\"/" \
#  Dockerfile && dedangle && ./bld
#ARG  TKT="tickets/DM-28302"
#ARG  BUILDTRIGGER="Tue Mar  2 09:49:12 MST 2021"
#RUN  pip3 install --upgrade \
#      git+https://github.com/lsst-sqre/rubin-jupyter-hub.git@${TKT} \
#      git+https://github.com/lsst-sqre/rubin-jupyter-helpers.git@${TKT} \
#      git+https://github.com/lsst-sqre/rubin-jupyter-config.git@${TKT} \
#      git+https://github.com/lsst-sqre/wfdispatcher.git # No branch
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
       version="0.4.4-pre3"
CMD [ "/usr/local/bin/start-wf-api" ]
