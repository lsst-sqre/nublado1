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

# Remove backup passwd/group/shadow files out of paranoia
rm -f /etc/passwd- /etc/shadow- /etc/group- /etc/gshadow-

# Check out notebooks-at-build-time
branch="prod"
notebooks="lsst-sqre/system-test rubin-dp0/tutorial-notebooks"
nbdir="/opt/lsst/software/notebooks-at-build-time"
owd=$(pwd)
source ${LOADRSPSTACK}
mkdir -p ${nbdir}
cd ${nbdir}
for n in ${notebooks}; do
    git clone -b ${branch} "https://github.com/${n}"
done
cd ${owd}
