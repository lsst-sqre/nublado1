FROM centos:7
USER root
RUN yum install -y nfs-utils
COPY write-keepalive.sh /
LABEL      description="jupyterlab demo: NFS Client" \
             name="lsstsqre/nfsclienttest" \
             version="0.0.3"
CMD [ "/write-keepalive.sh" ]


