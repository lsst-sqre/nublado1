FROM       centos:7
MAINTAINER sqre-admin
LABEL      description="Filebeat for Kubernetes nodes" \
           name="lsstsqre/k8s-filebeat" \
	   version="5.4.0"
ENV	   FILEBEAT_VERSION "5.4.0"
ENV        FILEBEAT_TGZ "filebeat-${FILEBEAT_VERSION}-linux-x86_64.tar.gz"
ENV        FILEBEAT_URL "https://artifacts.elastic.co/downloads/beats/filebeat/${FILEBEAT_TGZ}"
ENV        FILEBEAT_HOME /opt/filebeat-${FILEBEAT_VERSION}-linux-x86_64

USER       root
WORKDIR    /opt/
# If your network is horrible, create a local assets dir and dump the
#  file into it.
#COPY       assets/${FILEBEAT_TGZ} .
#RUN        tar xfz ${FILEBEAT_TGZ}
RUN        curl -sq ${FILEBEAT_URL} | tar xz -C .
ADD        filebeat.yml ${FILEBEAT_HOME}/
ADD        entrypoint.sh /entrypoint.sh
RUN        chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
