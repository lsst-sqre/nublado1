#!/bin/sh
shopt -q login_shell
rc=$?
if [ ${rc} -ne 0 ]; then
    case $- in
	*i*) cat /etc/motd
	     ;;
	*)
	     ;;
    esac
fi
