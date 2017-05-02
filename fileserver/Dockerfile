FROM centos:7
USER root
LABEL      description="jupyterlab demo: fileserver" \
             name="lsstsqre/jld-fileserver" \
             version="0.0.5"
#RUN  yum install -y epel-release
RUN  yum -y update
RUN  yum install -y iproute /usr/bin/ps nfs-utils sysvinit-tools
EXPOSE 20048/tcp 2049/tcp
VOLUME /exports/home
RUN  mkdir -p /exports/home
COPY exports.template substitute-network.sh /tmp/
COPY run_nfs.sh /usr/local/bin/run_nfs.sh
CMD [ "/usr/local/bin/run_nfs.sh" ]

