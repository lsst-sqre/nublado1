#!/bin/sh
sed -i -e '/tsflags\=nodocs/d' /etc/yum.conf
yum clean all
rpm -qa --qf "%{NAME}\n" | xargs yum -y reinstall
yum install -y epel-release
yum repolist
yum -y install $(cat ${verdir}/rpmlist.txt | xargs)
yum clean all
