#!/bin/sh
shopt -q login_shell
rc=$?
if [ ${rc} -ne 0 ]; then    # Not login
    if [ -n "${PS1}" ]; then # interactive
	cat /etc/motd
    fi
fi

