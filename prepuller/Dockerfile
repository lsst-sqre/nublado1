FROM centos:7
USER root
RUN  yum install -y epel-release
RUN  yum install -y python36 python36-pip git
# Make EPEL Python 3.6 system Python 3 and install pip3
RUN  alternatives --install /usr/bin/python3 python3 /usr/bin/python36 50 && \
      python3 -m ensurepip
RUN  alternatives --install /usr/bin/pip3 pip3 /usr/bin/pip3.6 50
RUN  yum -y update
RUN  pip3 install --upgrade pip
RUN  pip3 install jupyterhubutils
COPY prepull /usr/bin/prepull
RUN  chmod 0755 /usr/bin/prepull
CMD [ "/usr/bin/prepull" ]
LABEL      description="nublado: image prepuller" \
             name="lsstsqre/prepuller" \
             version="0.2.4"
