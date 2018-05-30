#!/bin/sh
PATH=/usr/local/texlive/2018/bin/x86_64-linux:/usr/local/bin:$PATH
PATH=$HOME/bin:$HOME/.local/bin:$PATH
MANPATH=Add /usr/local/texlive/2018/texmf-dist/doc/man:/usr/local/share/man:$MANPATH
INFOPATH=/usr/local/texlive/2018/texmf-dist/doc/info:/usr/local/share/info:$INFOPATH
export PATH MANPATH INFOPATH
