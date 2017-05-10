FROM lsstsqre/centos:7-stack-lsst_distrib-v13_0
USER root
LABEL      description="jupyterlab demo: jupyterlab (Python 2 LSST Stack)" \
             name="lsstsqre/jld-lab-py2" \
             version="0.0.7"
RUN  yum install -y epel-release
RUN  yum repolist
RUN  yum -y upgrade
RUN  yum -y install gcc python-pip python34 python34-pip python34-devel \
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
COPY assets/sqre_labkubespawner-0.0.1-py2.py3-none-any.whl \
     assets/jupyterlab-0.17.0-py2.py3-none-any.whl \
     /tmp/
# We do this with pip3/python3 because otherwise the Jupyterlab extension
#  doesn't load correctly and we do not get our Hub menu.
RUN  pip3 install /tmp/sqre_labkubespawner-0.0.1-py2.py3-none-any.whl \
      /tmp/jupyterlab-0.17.0-py2.py3-none-any.whl
RUN  source /opt/lsst/software/stack/loadLSST.bash && \
      pip install --upgrade pip && \
      pip install ipykernel /tmp/jupyterlab-0.17.0-py2.py3-none-any.whl
RUN  rm /tmp/jupyterlab-0.17.0-py2.py3-none-any.whl \     
      /tmp/sqre_labkubespawner-0.0.1-py2.py3-none-any.whl 
RUN  /opt/lsst/software/stack/Linux64/miniconda2/4.2.12.lsst1/bin/python \
      -m ipykernel install --name 'LSST_Stack'
RUN  python3 /usr/bin/jupyter serverextension enable --py jupyterlab \
      --sys-prefix
RUN  python3 /usr/bin/jupyter labextension install \
      sqre_labkubespawner \
      --py --sys-prefix
RUN  python3 /usr/bin/jupyter labextension enable \
       sqre_labkubespawner \
       --py --sys-prefix
RUN  /opt/lsst/software/stack/Linux64/miniconda2/4.2.12.lsst1/bin/python \
      /usr/bin/jupyter serverextension enable --py jupyterlab --sys-prefix
COPY local01-virtualenvwrapper.sh local02-hub.sh local03-showmotd.sh  \
     /etc/profile.d/
RUN  cd /etc/profile.d && \
     for i in local*; do \
         ln $i $(basename $i .sh).csh ;\
     done
RUN  mkdir -p /etc/skel/notebooks
RUN  mkdir -p /opt/lsst/software/jupyterlab/
COPY lsst_kernel_py2.json lsstlaunch.sh lablauncher.sh runlab.sh \
      /opt/lsst/software/jupyterlab/
COPY lsst_kernel_py2.json \
       /usr/local/share/jupyter/kernels/lsst_stack/kernel.json
COPY motd /etc/motd
COPY jupyter_notebook_config.json /usr/etc/jupyter
ENV  LANG=C.UTF-8
WORKDIR /tmp
CMD [ "/opt/lsst/software/jupyterlab/lablauncher.sh", "3" ]
