#!/usr/bin/env python3
"""Script to allow lab container to kill itself if idle or extant longer
than a threshold.
"""
import datetime
import json
import logging
import os
import pwd
import signal
import subprocess
import sys
import time
import urllib.request

from dateutil.parser import isoparse as parse_date

logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def cull_me(url, api_token, username, policy, timeout_i):
    """Shutdown this server if it's been idle or alive, depending on policy,
     too long.
    """
    # There is certainly some prettier way to find the first user-owned
    #  process (and thus the approximate age of the container), but life is
    #  too short.
    #
    # Kids, don't do it like this.
    #  Find the PIDs of the jupyter-labhub processes (should only be one...)
    #  Then sort them numerically, take the first (that is, the oldest) one
    #
    # If we are running under "debug", "runlab.sh" is the process (it executes
    #  labhub, waits after exit, and then restarts, so you can get into the
    #  container if labhub crashes).  If not, it's "jupyter-labhub"
    lcmd = "jupyter-labhub"
    debug = os.getenv('DEBUG')
    if debug:
        lcmd = "runlab.sh"
    get_jl_pid = "ps -C {} -o pid= | sort -n | head -1".format(lcmd)
    user_lab_pid = subprocess.check_output(
        [get_jl_pid], shell=True).decode('UTF-8').strip()
    age_t = subprocess.check_output(["ps", "-o", "etime=", "-p", user_lab_pid])
    # Sure, we could write an awful regex to parse the age.
    #  Or we could just do it like this.
    rtime = age_t.decode('UTF-8').strip()
    days = 0
    rflds = rtime.split('-')
    if len(rflds) > 1:
        rtime = rflds[1]
        days = int(rflds[0])
    hours = 0
    rflds = rtime.split(':')
    rflds.reverse()
    secs = int(rflds[0])
    mins = int(rflds[1])
    if len(rflds) > 2:
        hours = int(rflds[2])
    age = secs + 60 * mins + 60 * 60 * hours + 24 * 60 * 60 * days
    try:
        criterion, locality = policy.split(':', 2)
    except ValueError:
        criterion = policy
        locality = "remote"
    if not criterion:
        criterion = "idle"
    if not locality:
        locality = "remote"
    # We can expand this:
    oklocs = ["local", "remote"]
    okcrit = ["idle", "age"]
    if criterion not in okcrit:
        raise ValueError("Culling criteria must be in {}".format(okcrit))
    if locality not in oklocs:
        raise ValueError("Culling locality must be in {}".format(oklocs))
    auth_header = {}
    user = None
    if (locality == "remote" or criterion == "idle"):
        # 'age:local' doesn't need to make a remote call
        auth_header = {
            'Authorization': 'token %s' % api_token
        }
        req = urllib.request.Request(url=url + '/users/' + username,
                                     data=None,
                                     headers=auth_header)
        resp = urllib.request.urlopen(req)
        body = resp.read()
        user = json.loads(body.decode('utf8', 'replace'))
    now = datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc)
    inf = "Running culler: {} for {} with {} s timeout at {}".format(
        policy,
        username,
        timeout_i,
        str(now))
    logger.info(inf)
    cull_limit = now - datetime.timedelta(seconds=timeout_i)
    time_to_die = False
    if criterion == "idle":
        servers = user.get('servers')
        if not servers:
            logger.warning("No servers found for user [%s]." % username)
            return
        if len(servers) > 1:
            logger.warning(
                "Idle culler does not yet support multiple servers.")
            return
        server = servers.get('')
        if not server:
            logger.warning("Idle culler does not yet support named servers.")
            return
        last_activity_s = server.get('last_activity') or server.get('started')
        last_activity = parse_date(last_activity_s)
        if last_activity < cull_limit:
            time_to_die = True
    else:  # we only care about server age
        if age > timeout_i:
            time_to_die = True
    if time_to_die:
        # You can cull me anytime
        if criterion == "idle":
            logger.info("User [%s] inactive since [%s]" % (username,
                                                           last_activity_s))
        else:
            logger.info("User [%s] pod age [%d]s" % (username,
                                                     age))
        logger.info("Culling server for user [%s]" % username)
        if locality == "remote":
            req = urllib.request.Request(url=url +
                                         '/users/%s/server' % username,
                                         data=None,
                                         method='DELETE',
                                         headers=auth_header,
                                         )
            # Cull me!
            resp = urllib.request.urlopen(req)
            body = resp.read()
            logger.info("Culler response: [%s]" %
                        (body.decode('utf8', 'replace')))
        else:
            # Cull me!
            logger.info("Culling server (locally) for user [%s]" % username)
            logger.info("Attempting to kill process {}".format(user_lab_pid))
            os.kill(int(user_lab_pid), signal.SIGTERM)
    else:
        if criterion == "idle":
            logger.info("User [%s] last active [%s]; not culling." % (
                username, str(last_activity)))
        else:
            logger.info("User [%s] pod age [%d]s; not culling." % (
                username, age))


if __name__ == '__main__':
    # Assume that this has been updated (if necessary) from Service IP
    url = os.getenv('JUPYTERHUB_API_URL') or "http://localhost:8081/hub/api"
    username = os.getenv('JUPYTERHUB_USER') or pwd.getpwuid(os.getuid())[0]
    timeout = (os.getenv('JUPYTERLAB_CULL_TIMEOUT') or
               os.getenv('JUPYTERLAB_IDLE_TIMEOUT') or "600")
    policy = os.getenv('JUPYTERLAB_CULL_POLICY') or "idle:remote"
    debug = os.getenv('DEBUG')
    if debug:
        logger.setLevel(logging.DEBUG)
        logger.debug("Debug logging on.")
    try:
        timeout_i = int(timeout)
    except (ValueError, TypeError):
        logger.warning(
            "JUPYTERLAB_[IDLE/CULL]_TIMEOUT not parseable; no timeout.")
        sys.exit(0)
    if timeout_i <= 0:
        logger.warning(
            "JUPYTERLAB_[IDLE/CULL]_TIMEOUT negative or zero; no timeout.")
        sys.exit(0)
    delay = (int(0.5 + timeout_i / 2.0))
    if delay < 1:
        delay = 1
    if delay > 600:
        delay = 600
    api_token = os.getenv('JUPYTERHUB_API_TOKEN')
    logger.info("===Starting idle culler for user [%s]===" % username)
    logger.info("Polling delay {}s".format(delay))
    while True:
        cull_me(url, api_token, username, policy, timeout_i)
        time.sleep(delay)
