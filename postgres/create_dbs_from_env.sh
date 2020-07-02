#!/usr/bin/env bash

# We are going to expect environment variables to occur in triplets:
#  VRO_DB_XXX_USER, VRO_DB_XXX_PASSWORD, VRO_DB_XXX_DB

# For each one of those we find, we will write a clause that creates a
#  role, assigns it the password, and creates the database with that
#  role as owner.  Then we'll emit that clause to a startup SQL
#  script.  Having done _that_ we will spawn a reaper process which
#  will remove that script some time later (default: 120 seconds),
#  with the expectation that PostgreSQL will start up, create/alter
#  roles and schemas as needed, and be ready for use before the timer
#  expires and the files are removed.

mkdir -p ${PGDATA}

# Set admin user to "postgres" if unset.
if [ -z "$POSTGRES_USER" ]; then
    POSTGRES_USER="postgres"
    export POSTGRES_USER
fi

tdir=$(mktemp -d)
OUTPUT_FILE="${tdir}/vro.sql"
if [ -z "${SQL_ERASE_TIMEOUT}" ]; then
    SQL_ERASE_TIMEOUT=120
fi

:> ${OUTPUT_FILE} # Erase destination

alldb=$(env | sort -r | grep ^VRO_DB_ )
if [ -z "${alldb}" ]; then
    >&2 "No VRO-specific databases."
    # Nothing to do
    exit 0
fi
ids=""
for a in ${alldb}; do
    isuser=$(echo ${a} | grep _USER\=)
    if [ -n "${isuser}" ]; then
	# Get the _XXX_ part
	id=$(echo ${a} | cut -d '_' -f 3)
	if [ -z "${ids}" ]; then
	    ids="${id}"
	else
	    ids="${ids} ${id}"
	fi
    fi
done

# Now we have the list of identifiers.

if [ -z "${ids}" ]; then
    >&2 echo "No identifiers; no additional databases."
    exit 0
fi

for id in ${ids}; do
    errstr="found for DB identifier ${id}."
    prefix="VRO_DB_${id}"
    # Extract the values
    uvar="${prefix}_USER"
    pwvar="${prefix}_PASSWORD"
    dbvar="${prefix}_DB"
    user=${!uvar}
    pw=${!pwvar}
    db=${!dbvar}
    if [ -z "${user}" ]; then
	echo "No user ${errstr}!" 1>&2
	continue
    fi
    if [ -z "${pw}" ]; then
	echo "No password ${errstr}!" 1>&2
	continue
    fi
    if [ -z "${db}" ]; then
	echo "No database ${errstr}!" 1>&2
	continue
    fi
    istr=$(echo $errstr | cut -d ' ' -f 2-)
    # If we made it this far, we have all the components we need.

    # Make the role
    echo "-- role ${istr}" >> ${OUTPUT_FILE}
    echo "DO \$\$" >> ${OUTPUT_FILE}
    echo "BEGIN" >> ${OUTPUT_FILE}
    echo "  CREATE ROLE ${user} WITH NOLOGIN;" >> ${OUTPUT_FILE}
    echo "  EXCEPTION WHEN DUPLICATE_OBJECT THEN" >> ${OUTPUT_FILE}
    echo "  RAISE NOTICE 'role ${user} already exists';" >> ${OUTPUT_FILE}
    echo "END" >> ${OUTPUT_FILE}
    echo "\$\$;" >> ${OUTPUT_FILE}

    # Set the role's password

    echo "-- set password ${istr}" >> ${OUTPUT_FILE}
    echo "ALTER ROLE ${user} LOGIN ENCRYPTED PASSWORD '${pw}';" \
         >> ${OUTPUT_FILE}

    # Create the database
    echo "-- create database ${istr}" >> ${OUTPUT_FILE}
    echo "SELECT 'CREATE DATABASE ${db}' WHERE NOT EXISTS" \
	 "(SELECT FROM pg_database WHERE datname = '${db}')\\gexec" \
	 >> ${OUTPUT_FILE}

    # Change its ownership
    echo "-- change ownership ${istr}" >> ${OUTPUT_FILE}
    echo "ALTER DATABASE ${db} OWNER TO ${user};" >> ${OUTPUT_FILE}
done

psql -v ON_ERROR_STOP=0 --username "${POSTGRES_USER}" \
     --dbname "${POSTGRES_DB}" < ${OUTPUT_FILE}
rm -rf ${tdir}

