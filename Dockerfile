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
     pip install ipykernel jupyterlab
RUN  useradd -d /home/jupyterlab -m jupyterlab
USER jupyterlab
WORKDIR /home/jupyterlab
ENV  LANG=C.UTF-8
COPY jupyterhub_config.py .
COPY lsstlaunch.sh .
COPY ./run-jupyterhub.bash .
RUN  . virtualenvwrapper.sh && \
     mkvirtualenv -p $(which python3) py3 && \
     pip install jupyterhub jupyterlab ipykernel \
       jupyterhub-dummyauthenticator && \
     jupyter serverextension enable --py jupyterlab --sys-prefix       
RUN /opt/lsst/software/stack/Linux64/miniconda2/4.2.12.lsst1/bin/python \
       -m ipykernel install --prefix $HOME/.virtualenvs/py3 --name 'LSST_Stack'
COPY lsst_kernel.json \
       .virtualenvs/py3/share/jupyter/kernels/lsst_stack/kernel.json
COPY py3_kernel.json \
       .virtualenvs/py3/share/jupyter/kernels/python3/kernel.json
RUN  mkdir -p data       
CMD  [ "./run-jupyterhub.bash" ]
