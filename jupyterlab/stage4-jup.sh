#!/bin/sh
set -e
source ${LOADRSPSTACK}
mkdir -p ${jl}
for s in $SVXT; do \
    jupyter serverextension enable ${s} --py --sys-prefix ; \
done
for n in $NBXT; do \
    jupyter nbextension install ${n} --py --sys-prefix && \
    jupyter nbextension enable ${n} --py  --sys-prefix ; \
done
LBXT=$(cat ${verdir}/labext.txt) && \
for l in ${LBXT}; do \
    jupyter labextension install ${l} --no-build ; \
done
# Create package version docs.  Mamba env export doesn't work, while conda
# does.
mkdir -p ${instverdir} && \
      pip3 freeze > ${instverdir}/requirements-stack.txt && \
      mamba list --export > ${instverdir}/conda-stack.txt && \
      (rpm -qa | sort) > ${instverdir}/rpmlist.txt && \
      conda env export > ${instverdir}/conda-stack.yml
LBXT=$(cat ${verdir}/labext.txt) && \
for l in ${LBXT} ; do \
    jupyter labextension enable ${l} ; \
done
jupyter labextension disable "@jupyterlab/filebrowser-extension:share-file"
npm cache clean --force && \
jupyter lab clean && \
jupyter lab build --dev-build=False --minimize=False
jupyter labextension list 2>&1 | \
grep '^      ' | grep -v ':' | grep -v 'OK\*' | \
      awk '{print $1,$2}' | tr ' ' '@' > ${instverdir}/labext.txt
groupadd -g 768 jovyan
