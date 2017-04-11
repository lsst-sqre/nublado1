#!/bin/bash
set -x
source virtualenvwrapper.sh
workon py3
exec python -m ipykernel -f $1

