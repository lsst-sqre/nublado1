FROM library/postgres:12-alpine
RUN  mkdir -p /vro
COPY create_dbs.bash docker-entrypoint.sh /vro/
ENTRYPOINT [ "/vro/docker-entrypoint.sh" ]
LABEL description="Science Platform Notebook Aspect: postgres" \
       name="lsstsqre/lsp-postgres" \
       version="0.0.1"


