#!/bin/sh
scl="/opt/rh/rh-python36/root/usr/bin"
source scl_source enable rh-python36 && \
    ${scl}/python3 ${scl}/jupyterhub $*

