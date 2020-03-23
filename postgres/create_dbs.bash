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

OUTPUT_FILE=${INIT_SQL_FILE}
if [ -z "${OUTPUT_FILE}" ]; then
    OUTPUT_FILE="/docker-entrypoint-initdb.d/vro.sql"
fi
if [ -z "${SQL_ERASE_TIMEOUT}" ]; then
    SQL_ERASE_TIMEOUT=120
fi

:> ${OUTPUT_FILE} # Erase destination

alldb=$(env | sort -r | grep ^VRO_DB_)
identifiers=""
for a in ${alldb}; do
    isuser=$(echo ${a} | grep _USER\=)
    if [ -n "${isuser}" ]; then
	# Get the _XXX_ part
	id=$(echo ${a} | cut -d '_' -f 3)
	if [ -z "${users}" ]; then
	    identifiers="${id}"
	else
	    identifiers="${identifiers} ${id}"
	fi
    fi
done

# Now we have the list of identifiers.

for id in ${identifiers}; do
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
    echo "  CREATE ROLE ${user} WITH NOLOGIN" >> ${OUTPUT_FILE}
    echo "  EXCEPTION WHEN DUPLICATE_OBJECT THEN" >> ${OUTPUT_FILE}
    echo "  RAISE NOTICE 'role ${user} already exists'" >> ${OUTPUT_FILE}
    echo "END" >> ${OUTPUT_FILE}
    echo "\$\$;" >> ${OUTPUT_FILE}

    # Set the role's password

    echo "-- set password ${istr}" >> ${OUTPUT_FILE}
    echo "ALTER ROLE '${user}' LOGIN ENCRYPTED PASSWORD '${pw}'" \
         >> ${OUTPUT_FILE}

    # Create the database
    echo "-- create database ${istr}" >> ${OUTPUT_FILE}
    echo "SELECT 'CREATE DATABASE ${db}' WHERE NOT EXISTS" \
	 "(SELECT FROM pg_database WHERE datname = '${db}')\\gexec" \
	 >> ${OUTPUT_FILE}

    # Change its ownership
    echo "-- change ownership ${istr}" >> ${OUTPUT_FILE}
    echo "ALTER DATABASE '${db}' OWNER TO '${user}'" >> ${OUTPUT_FILE}
done

# Set the time bomb to erase the file
fn=$(mktemp)
echo "#!/bin/sh" > ${fn}
echo "sleep ${SQL_ERASE_TIMEOUT}" >> ${fn}
echo "rm -f ${OUTPUT_FILE}" >> ${fn}
echo "rm -f ${fn}" >> ${fn}
chmod 0700 ${fn}
nohup ${fn} 2>&1 > /dev/null &
