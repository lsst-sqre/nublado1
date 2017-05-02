FROM lsstsqre/centos:7-py3-demo
USER root
LABEL      description="jupyterlab demo: jupyterlab" \
             name="lsstsqre/jld-lab" \
             version="0.0.5"
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
     rm -rf ${F} ${FN} && \
     cd -
RUN  pip3 install --upgrade pip setuptools
RUN  pip2 install --upgrade pip setuptools
RUN  pip3 install virtualenv virtualenvwrapper 'jupyterlab<0.20' ipykernel
RUN  pip2 install virtualenv virtualenvwrapper
#       sqre_labkubespawner
COPY assets/sqre_labkubespawner-0.0.1-py2.py3-none-any.whl /tmp
RUN  pip3 install /tmp/sqre_labkubespawner-0.0.1-py2.py3-none-any.whl
RUN  rm /tmp/sqre_labkubespawner-0.0.1-py2.py3-none-any.whl
RUN  source /opt/lsst/software/stack/loadLSST.bash && \
     pip install --upgrade pip && \
     pip install ipykernel 'jupyterlab<0.20'
RUN  /opt/lsst/software/stack/miniconda3-4.2.12/bin/python \
      -m ipykernel install --name 'LSST_Stack'
RUN  python3 /usr/bin/jupyter serverextension enable --py jupyterlab \
      --sys-prefix
RUN  python3 /usr/bin/jupyter labextension install --py --sys-prefix \
      sqre_labkubespawner
RUN  python3 /usr/bin/jupyter labextension enable --py --sys-prefix \
      sqre_labkubespawner
RUN  /opt/lsst/software/stack/miniconda3-4.2.12/bin/python \
      /usr/bin/jupyter serverextension enable --py jupyterlab --sys-prefix
COPY local01-virtualenvwrapper.sh local02-hub.sh local03-showmotd.sh  \
     /etc/profile.d/
RUN  cd /etc/profile.d && \
     for i in local*; do \
         ln $i $(basename $i .sh).csh ;\
     done
RUN  mkdir -p /etc/skel/notebooks
RUN  mkdir -p /opt/lsst/software/jupyterlab/
COPY lsst_kernel.json lsstlaunch.sh lablauncher.sh runlab.sh \
      /opt/lsst/software/jupyterlab/
COPY lsst_kernel.json \
       /usr/local/share/jupyter/kernels/lsst_stack/kernel.json
COPY motd /etc/motd
COPY jupyter_notebook_config.json /usr/etc/jupyter
ENV  LANG=C.UTF-8
CMD [ "/opt/lsst/software/jupyterlab/lablauncher.sh" ]

