FROM lsstsqre/centos:7-stack-lsst_distrib-v13_0
USER root
LABEL      description="jupyterlab demo: jupyterlab" \
             name="lsstsqre/jld-lab" \
             version="0.0.1"
RUN  yum install -y epel-release
RUN  yum repolist
RUN  yum -y upgrade
RUN  yum -y install python-pip gcc python-devel nodejs npm git
RUN  pip install --upgrade pip setuptools
RUN  pip install virtualenv virtualenvwrapper 'jupyterlab<0.20' ipykernel \
       sqre_labkubespawner
RUN  source /opt/lsst/software/stack/loadLSST.bash && \
     pip install --upgrade pip && \
     pip install ipykernel 'jupyterlab<0.20'
COPY virtualenvwrapper.sh /etc/profile.d	
RUN  /opt/lsst/software/stack/Linux64/miniconda2/4.2.12.lsst1/bin/python \
      -m ipykernel install --name 'LSST_Stack'
RUN  python /usr/bin/jupyter serverextension enable --py jupyterlab \
      --sys-prefix
RUN  python /usr/bin/jupyter labextension install --py --sys-prefix \
      sqre_labkubespawner
RUN  jupyter labextension enable --py --sys-prefix sqre_labkubespawner
RUN  /opt/lsst/software/stack/Linux64/miniconda2/4.2.12.lsst1/bin/python \
      /usr/bin/jupyter serverextension enable --py jupyterlab --sys-prefix
RUN  mkdir -p /etc/skel/data
RUN  mkdir -p /opt/lsst/software/jupyterlab/
COPY lsst_kernel.json lsstlaunch.sh lablauncher.sh runlab.sh \
      /opt/lsst/software/jupyterlab/
COPY lsst_kernel.json \
       /usr/local/share/jupyter/kernels/lsst_stack/kernel.json
COPY motd /etc/motd
ENV  LANG=C.UTF-8
CMD [ "/opt/lsst/software/jupyterlab/lablauncher.sh" ]

