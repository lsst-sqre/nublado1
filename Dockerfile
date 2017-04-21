FROM lsstsqre/centos:7-stack-lsst_distrib-v13_0
USER root
LABEL      description="jupyterlab demo" \
             name="lsstsqre/jupyterlabdemo" \
             version="0.0.8"
RUN  yum install -y epel-release
RUN  yum repolist
RUN  yum install -y python34 python-pip python34-pip nodejs
RUN  pip3 install --upgrade pip
RUN  pip2 install --upgrade pip
RUN  pip3 install virtualenv virtualenvwrapper
RUN  pip2 install virtualenv virtualenvwrapper
RUN  npm install -g configurable-http-proxy
RUN  source /opt/lsst/software/stack/loadLSST.bash && \
     pip install 'ipython<6.0' jupyterlab
RUN  pip3 install jupyterhub jupyterlab ipykernel sqre-ghowlauth
RUN  /opt/lsst/software/stack/Linux64/miniconda2/4.2.12.lsst1/bin/python \
      -m ipykernel install --name 'LSST_Stack'
RUN  python3 /usr/bin/jupyter serverextension enable --py jupyterlab --sys-prefix
RUN  mkdir -p /opt/lsst/software/jupyterlab/
COPY lsst_kernel.json lsstlaunch.sh jupyterhub_config.py \
       /opt/lsst/software/jupyterlab/
COPY lsst_kernel.json \
       /usr/local/share/jupyter/kernels/lsst_stack/kernel.json
ENV  LANG=C.UTF-8
CMD  [ "/usr/bin/jupyterhub","--debug","-f",\
       "/opt/lsst/software/jupyterlab/jupyterhub_config.py" ]
