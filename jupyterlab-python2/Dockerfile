FROM lsstsqre/centos:7-stack-lsst_distrib-v13_0
USER root
RUN  groupadd -g 768 jupyter && chgrp -R jupyter /opt/lsst && \
      chmod -R g+w /opt/lsst
LABEL      description="jupyterlab demo: jupyterlab (Python 2 LSST Stack)" \
             name="lsstsqre/jld-lab-py2" \
             version="0.0.8"
RUN  yum install -y epel-release
RUN  yum repolist
RUN  yum -y upgrade
RUN  yum -y install python-pip python34 python34-pip gcc python34-devel \
      python-devel nodejs npm git jupyterlab
RUN  cd /tmp && \
     V="2.2.9" && \
     FN="hub-linux-amd64-${V}" && \
     F="${FN}.tgz" && \
     URL="https://github.com/github/hub/releases/download/v${V}/${F}" && \
     cmd="curl -L ${URL} -o ${F}" && \
     $cmd && \
     tar xpfz ${F} && \
     install -m 0755 ${FN}/bin/hub /usr/bin && \
     rm -rf ${F} ${FN}
RUN  pip3 install --upgrade pip setuptools
RUN  pip2 install --upgrade pip setuptools
RUN  pip3 install virtualenv virtualenvwrapper ipykernel nbdime \
      sqre-labkubespawner
RUN  pip2 install virtualenv virtualenvwrapper
# We need local notebook to get the equivalent of --allow-root
COPY assets/notebook-5.0.0.dev0-py2.py3-none-any.whl \
       /tmp/
RUN  pip3 install \
       /tmp/notebook-5.0.0.dev0-py2.py3-none-any.whl
RUN  python3 /usr/bin/nbdime config-git --enable --system
RUN  source /opt/lsst/software/stack/loadLSST.bash && \
      pip install --upgrade pip && \
      pip install ipykernel \
       /tmp/notebook-5.0.0.dev0-py2.py3-none-any.whl
ENV  MCD=Linux64/miniconda2/4.2.12.lsst1
RUN  /opt/lsst/software/stack/${MCD}/bin/python \
      -m ipykernel install --name 'LSST_Stack'
RUN  python3 /usr/bin/jupyter serverextension enable --py jupyterlab \
      --sys-prefix
RUN  /opt/lsst/software/stack/${MCD}/bin/python \
      /usr/bin/jupyter serverextension enable --py jupyterlab --sys-prefix
RUN  python3 /usr/bin/jupyter labextension install jupyterlab-hub
RUN  python3 /usr/bin/jupyter lab build
RUN  rm \
     /tmp/notebook-5.0.0.dev0-py2.py3-none-any.whl     
COPY local01-virtualenvwrapper.sh local02-hub.sh local03-showmotd.sh  \
     /etc/profile.d/
RUN  cd /etc/profile.d && \
     for i in local*; do \
         ln $i $(basename $i .sh).csh ;\
     done
RUN  mkdir -p /etc/skel/notebooks
RUN  mkdir -p /opt/lsst/software/jupyterlab/
COPY lsst_kernel_py2.json lsstlaunch.bash lablauncher.bash runlab.sh \
      /opt/lsst/software/jupyterlab/
RUN  chgrp -R jupyter /opt/lsst/software/jupyterlab && \
     chmod -R g+w /opt/lsst/software/jupyterlab
COPY lsst_kernel_py2.json \
       /usr/local/share/jupyter/kernels/lsst_stack/kernel.json
COPY motd /etc/motd
COPY jupyter_notebook_config.json /usr/etc/jupyter
ENV  LANG=C.UTF-8
WORKDIR /tmp
CMD [ "/opt/lsst/software/jupyterlab/lablauncher.bash" ]
