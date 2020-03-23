#!/usr/bin/env bash
source /vro/create_dbs.bash
exec /usr/local/bin/docker-entrypoint.sh "$@"
