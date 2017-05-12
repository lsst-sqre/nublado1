#!/bin/sh
file="/home/.keepalive"
while : ; do
    wstr="Writing keepalive to ${file} at $(date)"
    echo "${wstr}" | tee ${file}
    sleep 60
done
