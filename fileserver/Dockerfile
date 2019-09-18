FROM centos:7
USER root
RUN  yum -y update
RUN  yum install -y nfs-utils nfs4-acl-tools portmap
EXPOSE 2049/tcp
VOLUME /exports
ENV  EXPORTS="home scratch project software datasets software teststand"
RUN  for i in ${EXPORTS}; do \
         mkdir -p /exports/${i} ; \
	 echo "Fileserver built at $(date -u)" > /exports/${i}/.built ; \
     done 
COPY exports /etc/exports
COPY run_nfs.sh /usr/local/bin/run_nfs.sh
LABEL      description="LSP Notebook Aspect: fileserver (NFSv4)" \
             name="lsstsqre/sciplat-fileserver" \
             version="0.1.0"
CMD [ "/usr/local/bin/run_nfs.sh" ]

