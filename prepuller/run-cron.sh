#!/bin/bash
set -e

# Cron doesn't forward along it's environment variables from
# when it is started, but it should respect /etc/environment.
# Stuff our environment variables from starting in there.
/usr/bin/env > /etc/environment
exec /usr/sbin/crond -n -x sch,proc
