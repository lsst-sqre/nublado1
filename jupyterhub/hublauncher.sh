<<<<<<< HEAD
#!/bin/sh
set -x
=======
#!/bin/bash
>>>>>>> master
export HUB_CONNECT_IP=$(ifconfig | grep 'inet ' | awk '{print $2}' | \
			    grep -v '127.0.0.1')
exec /usr/bin/jupyterhub --debug -f \
      /opt/lsst/software/jupyterhub/jupyterhub_config.py
