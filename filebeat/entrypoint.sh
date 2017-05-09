#!/bin/sh
set -e

set_config() {
    KEY=$1
    VALUE=$2
    if [ -z "${VALUE}" ]; then
	echo "${KEY} must be set" 1>&2
	exit 1
    fi
    sed -i "s/{{${KEY}}}/${VALUE}/g" ${FILEBEAT_HOME}/filebeat.yml
}

if [ -z "${FILEBEAT_HOME}" ]; then
    echo "FILEBEAT_HOME must be set" 1>&2
    exit 1
fi

set_config "SHIPPER_NAME" "${SHIPPER_NAME}"
set_config "LOGSTASH_HOST" "${LOGSTASH_HOST}"
set_config "LOGSTASH_PORT" "${LOGSTASH_PORT}"
set_config "HOSTNAME" "$(hostname)"

exec ${FILEBEAT_HOME}/filebeat -c ${FILEBEAT_HOME}/filebeat.yml

