FROM centos:7
USER root
RUN  yum -y update
RUN  yum install -y iproute /usr/bin/ps nfs-utils sysvinit-tools
EXPOSE 20048/tcp 2049/tcp 111/tcp 111/udp
VOLUME /exports
RUN  for i in home scratch project software datasets; do \
         mkdir -p /exports/${i} ; \
	 echo "Fileserver built at $(date -u)" > /exports/${i}/.built ; \
     done 
COPY exports /etc/exports
COPY run_nfs.sh /usr/local/bin/run_nfs.sh
LABEL      description="jupyterlab demo: fileserver" \
             name="lsstsqre/jld-fileserver" \
             version="0.0.10"
CMD [ "/usr/local/bin/run_nfs.sh" ]

