#!/bin/sh
# Set up default user directory layout
set -e
for i in notebooks WORK DATA idleculler ; do \
   mkdir -p /etc/skel/${i} ; \
done

# "lsst" is a real GitHub organization, so rename the local user/group.
sed -i -e \
    's|^lsst:x:1000:1000::/home/lsst|lsst_lcl:x:1000:1000::/home/lsst_lcl|' \
    /etc/passwd
sed -i -e 's/^lsst:x:1000/lsst_lcl:x:1000/' /etc/group
pwconv
grpconv
if [ -d /home/lsst ]; then
    mv /home/lsst /home/lsst_lcl
fi

# Flag to signal that we can work without sudo enabled
echo "OK" > ${jl}/no_sudo_ok

# Add the provisioning user; we will soon be able to drop this
groupadd -g 769 provisionator
useradd -m -g provisionator -u 769 -c "Provisioning User" provisionator

# Remove backup passwd/group/shadow files out of paranoia
rm -f /etc/passwd- /etc/shadow- /etc/group- /etc/gshadow-
