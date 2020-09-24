#!/bin/sh

case "$-" in
    *i*)
        # OK, we're interactive.
        #  Are we a login shell?
        if shopt -q login_shell; then
	    # Yes.  Display the notice(s)
            if [ -e "/usr/local/etc/rsp_notice" ]; then
                cat /usr/local/etc/rsp_notice
	    fi
            msgdir="/opt/lsst/software/jupyterlab/messages.d"
            if [ -e  ${msgdir} ]; then
                any=$(ls ${msgdir})
                if [ -n "${any}" ]; then
                    cat ${msgdir}/*
                fi
            fi
	fi
        ;;
    *)
        ;;
esac
