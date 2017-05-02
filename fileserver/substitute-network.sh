#!/bin/sh

CLUSTERNET="$(ip addr show | grep 'inet ' | grep 'scope global' | \
		 awk '{print $2}' | cut -d '.' -f 1-2).0.0/16"

sed -e "s|{{CONTAINERS}}|${CLUSTERNET}|" < /tmp/exports.template > /etc/exports

