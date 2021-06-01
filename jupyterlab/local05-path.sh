#!/bin/sh
PATH=/usr/local/texlive/2021/bin/x86_64-linux:/usr/local/bin:$PATH
PATH=$HOME/bin:$HOME/.local/bin:$PATH
LD_LIBRARY_PATH=${LD_LIBRARY_PATH}:/usr/local/lib64
MANPATH=/usr/local/texlive/2021/texmf-dist/doc/man:/usr/local/share/man:$MANPATH
INFOPATH=/usr/local/texlive/2021/texmf-dist/doc/info:/usr/local/share/info:$INFOPATH
export PATH MANPATH INFOPATH LD_LIBRARY_PATH
