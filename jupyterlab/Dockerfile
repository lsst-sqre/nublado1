FROM lsstsqre/centos:7-py3-demo
USER root
LABEL      description="jupyterlab demo: jupyterlab" \
             name="lsstsqre/jld-lab-new" \
             version="0.0.4dev0"
RUN  yum install -y epel-release
RUN  yum repolist
RUN  yum -y upgrade
RUN  yum -y install python-pip python34 python34-pip gcc python34-devel \
      nodejs npm git
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
RUN  pip3 install virtualenv virtualenvwrapper ipykernel
RUN  pip2 install virtualenv virtualenvwrapper
COPY assets/sqre_labkubespawner-0.0.4.dev0-py2.py3-none-any.whl \
       assets/jupyterlab-0.21.0-py2.py3-none-any.whl \
       assets/notebook-5.0.0.dev0-py2.py3-none-any.whl \
       /tmp/
RUN  pip3 install /tmp/jupyterlab-0.21.0-py2.py3-none-any.whl \
       /tmp/sqre_labkubespawner-0.0.4.dev0-py2.py3-none-any.whl \
       /tmp/notebook-5.0.0.dev0-py2.py3-none-any.whl
RUN  source /opt/lsst/software/stack/loadLSST.bash && \
      pip3 install --upgrade pip && \
      pip3 install ipykernel /tmp/jupyterlab-0.17.0-py2.py3-none-any.whl \
       /tmp/sqre_labkubespawner-0.0.4.dev0-py2.py3-none-any.whl \
       /tmp/notebook-5.0.0.dev0-py2.py3-none-any.whl
RUN  /opt/lsst/software/stack/miniconda3-4.2.12/bin/python \
      -m ipykernel install --name 'LSST_Stack'
RUN  python3 /usr/bin/jupyter serverextension enable --py jupyterlab \
      --sys-prefix
RUN  python3 /usr/bin/jupyter labextension install \
#      jupyterhub_labextension \
      sqre_labkubespawner \
      --py --sys-prefix
RUN  python3 /usr/bin/jupyter labextension enable \
#      jupyterhub_labextension \
       sqre_labkubespawner \
       --py --sys-prefix
RUN  /opt/lsst/software/stack/miniconda3-4.2.12/bin/python \
      /usr/bin/jupyter serverextension enable --py jupyterlab --sys-prefix
RUN  rm /tmp/sqre_labkubespawner-0.0.4.dev0-py2.py3-none-any.whl \
     /tmp/jupyterlab-0.21.0-py2.py3-none-any.whl \
     /tmp/notebook-5.0.0.dev0-py2.py3-none-any.whl     
COPY local01-virtualenvwrapper.sh local02-hub.sh local03-showmotd.sh  \
     /etc/profile.d/
RUN  cd /etc/profile.d && \
     for i in local*; do \
         ln $i $(basename $i .sh).csh ;\
     done
RUN  mkdir -p /etc/skel/notebooks
RUN  mkdir -p /opt/lsst/software/jupyterlab/
COPY lsst_kernel.json lsstlaunch.bash lablauncher.bash runlab.bash \
      /opt/lsst/software/jupyterlab/
COPY lsst_kernel.json \
       /usr/local/share/jupyter/kernels/lsst_stack/kernel.json
COPY motd /etc/motd
COPY jupyter_notebook_config.json /usr/etc/jupyter
ENV  LANG=C.UTF-8
WORKDIR /tmp
CMD [ "/opt/lsst/software/jupyterlab/lablauncher.sh" ]

