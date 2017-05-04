FROM        nginx
MAINTAINER  sqre-admin
LABEL       description="SSL termination/proxy for SQuaRE Jupyterlab demo" \
            name="lsstsqre/k8s-jupyterlabdemo-nginx"
ARG         VERSION="0.0.2"
LABEL       version="$VERSION"
COPY        nginx.conf /
COPY        entrypoint.sh /
RUN         chmod 0755 /entrypoint.sh
EXPOSE      80 443
ENTRYPOINT  ["/entrypoint.sh"]
