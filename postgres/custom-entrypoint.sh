#!/usr/bin/env bash
set -Eeo pipefail
source "$(command -v docker-entrypoint.sh)"

docker_create_db_directories() {
        # This also has to work on NFS with root_squash set, so....
        local user; user="$(id -u)"

        mkdir -p "$PGDATA" || :
        chmod 700 "$PGDATA" || :

        if [ "${user}" = '0' ]; then
            if [ ! -d "${PGDATA}" ]; then
                su-exec postgres mkdir -p "${PGDATA}"
	    else
		chown postgres "${PGDATA}" || :
		# This might fail under root_squash.
		# But in that case we'd hope that the top dir was already
		#  owned by postgres.  So we suppress failure to trick
		#  the set -e .
            fi
            su-exec postgres chmod 700 "${PGDATA}"
        fi

        # ignore failure since it will be fine when using the image provided directory; see also https://github.com/docker-library/postgres/pull/289
        mkdir -p /var/run/postgresql || :
        chmod 775 /var/run/postgresql || :

        # Create the transaction log directory before initdb is run so the directory is owned by the correct user
        if [ -n "$POSTGRES_INITDB_WALDIR" ]; then
                mkdir -p "$POSTGRES_INITDB_WALDIR"
                if [ "$user" = '0' ]; then
                        find "$POSTGRES_INITDB_WALDIR" \! -user postgres -exec chown postgres '{}' + || :
                        su-exec postgres find "$POSTGRES_INITDB_WALDIR" \! -user postgres -exec chown postgres '{}' +
                fi
                chmod 700 "$POSTGRES_INITDB_WALDIR" || :
        fi

        # allow the container to be started with `--user`
        if [ "$user" = '0' ]; then
                find "$PGDATA" \! -user postgres -exec chown postgres '{}' + || :
                find /var/run/postgresql \! -user postgres -exec chown postgres '{}' + || :
                su-exec postgres find "$PGDATA" \! -user postgres -exec chown postgres '{}' +
                su-exec postgres find /var/run/postgresql \! -user postgres -exec chown postgres '{}' +
        fi
}


_main() {
        # if first arg looks like a flag, assume we want to run postgres server
        if [ "${1:0:1}" = '-' ]; then
                set -- postgres "$@"
        fi

        if [ "$1" = 'postgres' ] && ! _pg_want_help "$@"; then
                docker_setup_env
                # setup data directories and permissions (when run as root)
                docker_create_db_directories
                if [ "$(id -u)" = '0' ]; then
                        # then restart script as postgres user
                        exec su-exec postgres "$BASH_SOURCE" "$@"
                fi

                # only run initialization on an empty data directory
                if [ -z "$DATABASE_ALREADY_EXISTS" ]; then
                        docker_verify_minimum_env

                        # check dir permissions to reduce likelihood of half-initialized database
                        ls /docker-entrypoint-initdb.d/ > /dev/null

                        docker_init_database_dir
                        pg_setup_hba_conf

                        # PGPASSWORD is required for psql when authentication is required for 'local' connections via pg_hba.conf and is otherwise harmless
                        # e.g. when '--auth=md5' or '--auth-local=md5' is used in POSTGRES_INITDB_ARGS
                        export PGPASSWORD="${PGPASSWORD:-$POSTGRES_PASSWORD}"
                        docker_temp_server_start "$@"

                        docker_setup_db
                        docker_process_init_files /docker-entrypoint-initdb.d/*

                        docker_temp_server_stop
                        unset PGPASSWORD

                        echo
                        echo 'PostgreSQL init process complete; ready for start up.'
                        echo
                else
                        echo
                        echo 'PostgreSQL Database directory appears to contain a database; Skipping initialization'
                        echo
                fi
                # Additional
                echo 'Running /always-initdb.d/* files'
                docker_temp_server_start "$@"
                docker_process_init_files /always-initdb.d/*
                docker_temp_server_stop
        fi

        exec "$@"
}

if ! _is_sourced; then
        _main "$@"
fi
