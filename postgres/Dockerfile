FROM library/postgres:12-alpine
COPY create_dbs.sh /docker-entrypoint-initdb.d
LABEL description="Science Platform Notebook Aspect: postgres" \
       name="lsstsqre/lsp-postgres" \
       version="0.0.2"
