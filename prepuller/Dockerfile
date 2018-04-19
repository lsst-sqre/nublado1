FROM centos:7
USER root
RUN  yum install -y epel-release
RUN  yum install -y python34 python34-pip git
RUN  yum -y update
RUN  pip3 install --upgrade pip
RUN  pip3 install  https://github.com/lsst-sqre/jupyterutils/zipball/master
COPY prepull /usr/bin/prepull
RUN  chmod 0755 /usr/bin/prepull
CMD [ "/usr/bin/prepull" ]
LABEL      description="jupyterlab demo: imageprepuller" \
             name="lsstsqre/prepuller" \
             version="0.1.2"
