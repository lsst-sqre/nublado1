#!/bin/sh
while : ; do
    for i in home project scratch; do
	file="/${i}/.keepalive"
	wstr="Writing keepalive to ${file} at $(date)"
	echo "${wstr}" | tee ${file}
    done
    sleep 60
done
