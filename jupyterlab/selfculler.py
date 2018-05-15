#!/usr/bin/env python3
"""script to allow lab container to kill itself if idle longer than a
threshold.
"""
import datetime
import json
import logging
import os
import pwd
import sys
import time
import urllib.request

from dateutil.parser import isoparse as parse_date

logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def cull_me(url, api_token, username, timeout_i):
    """Shutdown this server if it's been idle too long.
    """
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
    logger.info("Running culler for [%s] with [%d] second timeout at [%s]" %
                (username, timeout_i, str(now)))
    cull_limit = now - datetime.timedelta(seconds=timeout_i)
    # shutdown server
    servers = user.get('servers')
    if not servers:
        logger.warning("No servers found for user [%s]." % username)
        return
    if len(servers) > 1:
        logger.warning("Idle culler does not yet support multiple servers.")
        return
    server = servers.get('')
    if not server:
        logger.warning("Idle culler does not yet support named servers.")
        return
    last_activity_s = server.get('last_activity') or server.get('started')
    last_activity = parse_date(last_activity_s)
    if last_activity < cull_limit:
        # You can cull me anytime
        logger.info("User [%s] inactive since [%s]" % (username,
                                                       last_activity_s))
        logger.info("Culling server for user [%s]" % username)
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
        logger.info("User [%s] last active [%s]; not culling." % (
            username, str(last_activity)))


if __name__ == '__main__':
    # Assume that this has been updated (if necessary) from Service IP
    url = os.getenv('JUPYTERHUB_API_URL') or "http://localhost:8081/hub/api"
    username = os.getenv('JUPYTERHUB_USER') or pwd.getpwuid(os.getuid())[0]
    timeout = os.getenv('JUPYTERLAB_IDLE_TIMEOUT') or "600"
    debug = os.getenv('DEBUG')
    if debug:
        logger.setLevel(logging.DEBUG)
        logger.debug("Debug logging on.")
    try:
        timeout_i = int(timeout)
    except (ValueError, TypeError) as e:
        logger.warning(
            "JUPYTERLAB_IDLE_TIMEOUT unset or negative; no timeout.")
        sys.exit(0)
    delay = (int(0.5 + timeout_i / 2.0))
    if delay < 1:
        delay = 1
    if delay > 600:
        delay = 600
    api_token = os.getenv('JUPYTERHUB_API_TOKEN')
    logger.info("===Starting idle culler for user [%s]===" % username)
    while True:
        cull_me(url, api_token, username, timeout_i)
        time.sleep(delay)
