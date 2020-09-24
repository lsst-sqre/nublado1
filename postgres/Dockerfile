FROM library/postgres:12-alpine
# The default, /var/lib/postgresql/data, is its own volume.  Sigh.
ENV  PGDATA /var/lib/postgresql/pgdata
RUN  mkdir -p /always-initdb.d && chown -R postgres /always-initdb.d
COPY create_dbs_from_env.sh /always-initdb.d
# We need a custom entrypoint to run all our initdb script
#  (which is idempotent) whether or not the overall database exists.
COPY custom-entrypoint.sh /usr/local/bin/
RUN  chmod 0755 /usr/local/bin/custom-entrypoint.sh
ENTRYPOINT ["custom-entrypoint.sh"]
CMD ["postgres"]
LABEL description="Science Platform Notebook Aspect: postgres" \
       name="lsstsqre/lsp-postgres" \
       version="0.0.5"
