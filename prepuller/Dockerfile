FROM centos:7
USER root
LABEL      description="jupyterlab demo: imageprepuller" \
             name="lsstsqre/prepuller" \
             version="0.0.1"
RUN  yum install -y cronie epel-release
RUN  yum install -y python34
RUN  yum -y update
COPY get_builds.py /usr/bin/get_builds
COPY imagepuller /etc/cron.hourly/local01-imagepuller
RUN  chmod 0755 /usr/bin/get_builds /etc/cron.hourly/local01-imagepuller
CMD [ "/usr/sbin/crond", "-n", "-x",  "sch,proc" ]

