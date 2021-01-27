#!/bin/sh
# This will be an interactive system, so we do want man pages after all
sed -i -e '/tsflags\=nodocs/d' /etc/yum.conf
yum clean all
rpm -qa --qf "%{NAME}\n" | xargs yum -y reinstall
yum install -y epel-release man man-pages
yum repolist
yum -y upgrade
# Add some other packages
#  sudo can be dropped soon
#  gettext and fontconfig are needed for the TexLive installation
#  jq ... file are generally useful utilities
#  ...and finally enough editors to cover most people's habits
yum -y install \
    sudo \
    gettext fontconfig \
    jq unzip ack screen tmux tree file \
    nano vim-enhanced emacs-nox ed
# Clear build cache
yum clean all
