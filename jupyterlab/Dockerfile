FROM lsstsqre/centos:7-stack-lsst_distrib-v13_0
USER root
LABEL      description="jupyterlab demo: jupyterlab" \
             name="lsstsqre/jld-lab-new" \
             version="0.0.4dev0"
RUN  yum install -y epel-release
RUN  yum repolist
RUN  yum -y upgrade
RUN  yum -y install python-pip gcc python-devel nodejs npm git
RUN  pip install --upgrade pip setuptools
RUN  pip install virtualenv virtualenvwrapper ipykernel \
     jupyterlab-launcher
#       sqre_labkubespawner
COPY assets/sqre_labkubespawner-0.0.4.dev0-py2.py3-none-any.whl \
     assets/jupyterlab-0.21.0-py2.py3-none-any.whl \
     assets/notebook-5.0.0.dev0-py2.py3-none-any.whl \
     /tmp/
RUN  pip install /tmp/jupyterlab-0.21.0-py2.py3-none-any.whl \
     /tmp/sqre_labkubespawner-0.0.4.dev0-py2.py3-none-any.whl \
     /tmp/notebook-5.0.0.dev0-py2.py3-none-any.whl
RUN  source /opt/lsst/software/stack/loadLSST.bash && \
     pip install --upgrade pip && \
     pip install ipykernel /tmp/jupyterlab-0.21.0-py2.py3-none-any.whl \
       /tmp/notebook-5.0.0.dev0-py2.py3-none-any.whl
RUN  rm /tmp/sqre_labkubespawner-0.0.4.dev0-py2.py3-none-any.whl \
     /tmp/jupyterlab-0.21.0-py2.py3-none-any.whl \
     /tmp/notebook-5.0.0.dev0-py2.py3-none-any.whl     
RUN  /opt/lsst/software/stack/Linux64/miniconda2/4.2.12.lsst1/bin/python \
      -m ipykernel install --name 'LSST_Stack'
#RUN  python /usr/bin/jupyter serverextension enable --py jupyterlab \
#      --sys-prefix
#RUN  python /usr/bin/jupyter labextension install --py --sys-prefix \
#      sqre_labkubespawner
#RUN  jupyter labextension enable --py --sys-prefix sqre_labkubespawner
#RUN  /opt/lsst/software/stack/Linux64/miniconda2/4.2.12.lsst1/bin/python \
#      /usr/bin/jupyter serverextension enable --py jupyterlab --sys-prefix
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
RUN  cd /tmp && \
     export V="2.2.9" && \
     export FN="hub-linux-amd64-${V}" && \
     export F="${FN}.tgz" && \
     wget https://github.com/github/hub/releases/download/v${V}/${F} && \
     tar xpfz ${F} && \
     install ${FN}/bin/hub /usr/bin && \
     rm -rf ${FN} ${F} && \
     cd -
COPY jupyter_notebook_config.json /usr/etc/jupyter/
ENV  LANG=C.UTF-8
CMD [ "/opt/lsst/software/jupyterlab/lablauncher.bash" ]

