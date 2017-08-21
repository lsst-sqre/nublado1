#!/bin/sh
set -e
set_config() {
    KEY=$1
    VALUE=$(eval echo \$${KEY})
    if [ -z "${VALUE}" ]; then
        echo "${KEY} must be set" 1>&2
        exit 1
    fi
    sed -i "s/{{${KEY}}}/${VALUE}/g" /nginx.conf
}

env|sort

if [ -z "${FIREFLY_SERVICE_HOST}" ]; then
    FIREFLY_SERVICE_HOST=${JLD_HUB_SERVICE_HOST}
fi
if [ -z "${FIREFLY_SERVICE_PORT}" ]; then
    FIREFLY_SERVICE_PORT=${JLD_HUB_SERVICE_PORT}
fi

set_config HOSTNAME
for i in JLD_HUB FIREFLY; do
    for j in HOST PORT; do
	set_config ${i}_SERVICE_${j}
    done
done
echo "----nginx.conf----"
cat /nginx.conf
echo "------------------"
exec nginx -c /nginx.conf -g 'daemon off;'
