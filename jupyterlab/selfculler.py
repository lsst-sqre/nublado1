#!/usr/bin/env python3
"""script to allow lab container to kill itself if idle longer than a
threshold.
"""
import datetime
import json
import os
import pwd
import sys
import time
import urllib.request

from dateutil.parser import parse as parse_date


def cull_me(url, api_token, username, timeout_i):
    """Shutdown idle single-user servers
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
    now = datetime.datetime.utcnow()
    print("Running culler for %s with %d second timeout at %s" %
          (username, timeout_i, str(now)))
    cull_limit = now - datetime.timedelta(seconds=timeout_i)
    # shutdown server
    if user['server']:
        last_activity = parse_date(user['last_activity'])
        name = user['name']
        if last_activity < cull_limit:
            print("User [%s] inactive since [%s]" % (name,
                                                     str(last_activity)))
            req = urllib.request.Request(url=url + '/users/%s/server' % name,
                                         data=None,
                                         method='DELETE',
                                         headers=auth_header,
                                         )
            resp = urllib.request.urlopen(req)
            body = resp.read()
            print("Response: [%s]" % (body.decode('utf8', 'replace')))
        else:
            print("User [%s] last active [%s]" % (name, str(last_activity)))

if __name__ == '__main__':
    url = os.getenv('JUPYTERHUB_API_URL') or "http://localhost:8081/hub/api"
    username = os.getenv('JUPYTERHUB_USER') or pwd.getpwuid(os.getuid())[0]
    timeout = os.getenv('JUPYTERLAB_IDLE_TIMEOUT') or "600"
    try:
        timeout_i = int(timeout)
    except (ValueError, TypeError) as e:
        print("JUPYTERLAB_IDLE_TIMEOUT not set or negative; no timeout.")
        sys.exit(0)
    delay = (int(0.5 + timeout_i / 2.0))
    if delay < 1:
        delay = 1
    if delay > 600:
        delay = 600
    api_token = os.environ['JUPYTERHUB_API_TOKEN']
    print("===Starting idle culler===")
    while True:
        cull_me(url, api_token, username, timeout_i)
        time.sleep(delay)
