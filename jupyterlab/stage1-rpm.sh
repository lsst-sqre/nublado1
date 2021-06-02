#!/bin/sh
# This will be an interactive system, so we do want man pages after all
sed -i -e '/tsflags\=nodocs/d' /etc/yum.conf
yum clean all
yum install -y epel-release man man-pages
yum repolist
yum -y upgrade
rpm -qa --qf "%{NAME}\n" | xargs yum -y reinstall
# Add some other packages
#  sudo can be dropped soon
#  gettext and fontconfig are needed for the TexLive installation
#  jq ... file are generally useful utilities
#  ...and finally enough editors to cover most people's habits
yum -y install \
    gettext fontconfig perl-MD5-Digest \
    jq unzip ack screen tmux tree file \
    nano vim-enhanced emacs-nox ed
# Clear build cache
yum clean all
