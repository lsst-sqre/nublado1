FROM centos:7
USER root
RUN  yum -y update
RUN  yum install -y nfs-utils
COPY write-keepalive.sh /
LABEL      description="nublado: NFS v4 Client" \
             name="lsstsqre/nfsclienttest" \
             version="0.1.0"
CMD [ "/write-keepalive.sh" ]


