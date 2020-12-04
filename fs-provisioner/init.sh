#!/bin/sh
set -e
# This provisions our directories on a Filestore-like system where we
#  can mount the toplevel volume as root, and create our exported directories
#  immediately underneath that.
#
# The pod will mount the toplevel volume to /storage
MOUNTPOINTS="home project datasets scratch"

for m in ${MOUNTPOINTS}; do
    localmt="/storage/${m}"
    mkdir -p ${localmt}
    if [ "${m}" == "scratch" ]; then
	chmod 1777 ${localmt}
    fi
done

echo "Storage provisioning complete at $(date)"
exit 0

