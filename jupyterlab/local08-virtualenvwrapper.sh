#!/bin/sh
# Source virtualenvwrapper.sh
# This must happen *after* the python scl is enabled.
if [ $(id -u) -ne 0 ]; then
    source $(which virtualenvwrapper.sh)
    rc=$?
    if [ "${rc}" -ne 0 ]; then
	alias python='python3'
	source $(which virtualenvwrapper.sh)
	unalias python
    fi
fi

