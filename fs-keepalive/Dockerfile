FROM centos:7
USER root
RUN  yum -y update
RUN  yum install -y nfs-utils
COPY write-keepalive.sh /
LABEL      description="nublado: NFS Client" \
             name="lsstsqre/nfsclienttest" \
             version="0.0.4"
CMD [ "/write-keepalive.sh" ]


