#!/bin/sh
set -e
mkdir -p ${jl}
source ${LOADRSPSTACK}
for s in $SVXT; do
    jupyter serverextension enable ${s} --py --sys-prefix
done
for n in $NBXT; do
    jupyter nbextension install ${n} --py --sys-prefix
    jupyter nbextension enable ${n} --py  --sys-prefix
done
for l in ${LBXT}; do
    jupyter labextension install ${l} --no-build
done

# Create package version docs.
#  conda env export works where mamba env export does not
#  We actually only use conda-stack.yml, rpmlist.txt, and labext.txt now
#  when building the pinned version of the container.
mkdir -p ${verdir}
pip3 freeze > ${verdir}/requirements-stack.txt
mamba list --export > ${verdir}/conda-stack.txt
conda env export > ${verdir}/conda-stack-orig.yml
# Pyjs9 is installed from git, and thus neither from conda nor PyPi.
#  The conda env just sees that it's version 3.3.
grep -v 'pyjs9' ${verdir}/conda-stack-orig.yml > ${verdir}/conda-stack.yml
rm ${verdir}/conda-stack-orig.yml
rpm -qa | sort > ${verdir}/rpmlist.txt
for l in ${LBXT} ; do
    jupyter labextension enable ${l}
done
jupyter labextension disable \
      "@jupyterlab/filebrowser-extension:share-file"
npm cache clean --force
jupyter lab clean
jupyter lab build --dev-build=False --minimize=False
# List installed labextensions and put them into a format we can consume for
#  the pinned builds.
jupyter labextension list 2>&1 | \
      grep '^      ' | grep -v ':' | grep -v 'OK\*' | \
      awk '{print $1,$2}' | tr ' ' '@' > ${verdir}/labext.txt
# Not clear we need the jovyan group anymore
groupadd -g 768 jovyan 
