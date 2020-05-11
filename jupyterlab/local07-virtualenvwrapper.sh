#!/bin/sh
# Source virtualenvwrapper.sh
# Use python3, *not* the system Python 2.
if [ $(id -u) -ne 0 ]; then
    pver=$(python -V 2>&1 | cut -d ' ' -f 2 | cut -d '.' -f 1)
    if [ ${pver} -lt 3 ]; then
	VIRTUALENVWRAPPER_PYTHON="$(command \which python3)" \
				source $(which virtualenvwrapper.sh)
    else
	source $(which virtualenvwrapper.sh)
    fi
fi

