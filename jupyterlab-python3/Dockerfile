FROM lsstsqre/centos:7-py3-demo
USER root
RUN  groupadd -g 768 jupyter && chgrp -R jupyter /opt/lsst && \
      chmod -R g+w /opt/lsst
RUN  yum install -y epel-release
RUN  yum repolist
RUN  yum -y upgrade
RUN  yum -y install python-pip python34 python34-pip gcc python34-devel \
      python-devel nodejs npm git
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
      sqre-labkubespawner jupyterlab
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
ENV  MCD=miniconda3-4.2.12
ENV  PYVER=3
RUN  /opt/lsst/software/stack/${MCD}/bin/python \
      -m ipykernel install --name 'LSST_Stack'
RUN  python3 /usr/bin/jupyter serverextension enable --py jupyterlab \
      --sys-prefix
RUN  /opt/lsst/software/stack/${MCD}/bin/python \
      /usr/bin/jupyter serverextension enable --py jupyterlab --sys-prefix
# If jupyterlab-hub isn't updated on npm, you need the git + local build
#RUN  python3 /usr/bin/jupyter labextension install jupyterlab-hub
#RUN  python3 /usr/bin/jupyter lab build
RUN  mkdir -p /usr/share/git && cd /usr/share/git && \
     git clone https://github.com/jupyterhub/jupyterlab-hub.git && \
     cd jupyterlab-hub && \
     npm install && \
     python3 /usr/bin/jupyter labextension link . && \
     cd /usr/share/git/jupyterlab-hub && \
     npm run build && \
     python3 /usr/bin/jupyter lab build
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
COPY lsst_kernel_py${PYVER}.json \
      lsstlaunch.bash lablauncher.bash runlab.sh \
      /opt/lsst/software/jupyterlab/
COPY lsst_kernel_py${PYVER}.json \
       /usr/local/share/jupyter/kernels/lsst_stack/kernel.json
RUN  chgrp -R jupyter /opt/lsst/software/jupyterlab && \
     chmod -R g+w /opt/lsst/software/jupyterlab && \
     chgrp -R jupyter /usr/share/jupyter/lab && \
     chmod -R g+wt /usr/share/jupyter/lab
COPY motd /etc/motd
COPY jupyter_notebook_config.json /usr/etc/jupyter
ENV  LANG=C.UTF-8
WORKDIR /tmp
CMD [ "/opt/lsst/software/jupyterlab/lablauncher.bash" ]
LABEL      description="jupyterlab demo: jupyterlab (Python 3 LSST Stack)" \
             name="lsstsqre/jld-lab-py3" \
             version="0.1.0"
