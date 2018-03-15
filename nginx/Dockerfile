FROM        nginx
MAINTAINER  sqre-admin
LABEL       description="SSL termination/proxy for SQuaRE Jupyterlab demo + Firefly" \
            name="lsstsqre/jld-nginx" \
	    version="0.0.5"
COPY        nginx.conf /
COPY        entrypoint.sh /
RUN         chmod 0755 /entrypoint.sh
EXPOSE      80 443
ENTRYPOINT  ["/entrypoint.sh"]
