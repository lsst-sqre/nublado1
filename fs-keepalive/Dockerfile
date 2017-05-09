FROM centos:7
USER root
LABEL      description="jupyterlab demo: NFS Client" \
             name="lsstsqre/nfsclienttest" \
             version="0.0.2"
#RUN  yum install -y epel-release
RUN yum install -y nfs-utils
COPY write-keepalive.sh /
CMD [ "/write-keepalive.sh" ]


