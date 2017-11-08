"""
This authenticator uses GitHub organization membership to make authentication
and authorization decisions.
"""
import datetime
import json
import os
import oauthenticator
import urllib
from oauthenticator.common import next_page_from_links
from tornado import gen
from tornado.httpclient import HTTPRequest, AsyncHTTPClient, HTTPError


# Utility definitions from GitHub OAuthenticator.

# Support github.com and github enterprise installations
GITHUB_HOST = os.environ.get('GITHUB_HOST') or 'github.com'
if GITHUB_HOST == 'github.com':
    GITHUB_API = 'api.github.com'
else:
    GITHUB_API = '%s/api/v3' % GITHUB_HOST


def _api_headers(access_token):
    return {"Accept": "application/json",
            "User-Agent": "JupyterHub",
            "Authorization": "token {}".format(access_token)
            }


# Request additional scope on GitHub token to auto-provision magic in the
# user container.
class LSSTLoginHandler(oauthenticator.GitHubLoginHandler):
    """Request additional scope on GitHub token.
    """
    scope = ['public_repo', 'read:org', 'user:email']


# Enable the authenticator to spawn with additional information acquired
# with token with larger-than-default scope.
class LSSTAuth(oauthenticator.GitHubOAuthenticator):
    """Authenticator to use our custom environment settings.
    """
    enable_auth_state = True

    _state = None

    login_handler = LSSTLoginHandler

    @gen.coroutine
    def pre_spawn_start(self, user, spawner):
        # First pulls can be really slow for the LSST stack containers,
        #  so let's give it a big timeout
        spawner.http_timeout = 60 * 15
        spawner.start_timeout = 60 * 15
        # The spawned containers need to be able to talk to the hub through
        #  the proxy!
        spawner.hub_connect_port = int(os.environ['JLD_HUB_SERVICE_PORT'])
        spawner.hub_connect_ip = os.environ['JLD_HUB_SERVICE_HOST']
        # Set up memory and CPU upper/lower bounds
        memlim = os.getenv('LAB_MEM_LIMIT')
        if not memlim:
            memlim = '2G'
        memguar = os.getenv('LAB_MEM_GUARANTEE')
        if not memguar:
            memguar = '64K'
        cpulimstr = os.getenv('LAB_CPU_LIMIT')
        cpulim = 1.0
        if cpulimstr:
            cpulim = float(cpulimstr)
        cpuguar = 0.02
        cpuguarstr = os.getenv('LAB_CPU_GUARANTEE')
        if cpuguarstr:
            cpuguar = float(cpuguarstr)
        spawner.mem_limit = memlim
        spawner.cpu_limit = cpulim
        spawner.mem_guarantee = memguar
        spawner.cpu_guarantee = cpuguar
        # Persistent shared user volume
        volname = "jld-fileserver-home"
        homefound = False
        for v in spawner.volumes:
            if v["name"] == volname:
                homefound = True
                break
        if not homefound:
            spawner.volumes.extend([
                {"name": volname,
                 "persistentVolumeClaim":
                 {"claimName": volname}}])
            spawner.volume_mounts.extend([
                {"mountPath": "/home",
                 "name": volname}])
        # We are running the Lab at the far end, not the old Notebook
        spawner.default_url = '/lab'
        spawner.singleuser_image_pull_policy = 'Always'
        self._make_options_form(spawner)
        # Add extra configuration from auth_state
        if not self.enable_auth_state:
            return
        auth_state = yield user.get_auth_state()
        gh_user = auth_state.get("github_user")
        gh_token = auth_state.get("access_token")
        if gh_user:
            gh_id = gh_user.get("id")
        gh_org = yield self._get_user_organizations(gh_token)
        gh_email = gh_user.get("email")
        if not gh_email:
            gh_email = yield self._get_user_email(gh_token)
        if gh_email:
            spawner.environment['GITHUB_EMAIL'] = gh_email
        gh_name = gh_user.get("name")
        if not gh_name:
            gh_name = gh_user.get("login")
        if gh_id:
            spawner.environment['EXTERNAL_UID'] = str(gh_id)
        if gh_org:
            orglstr = ""
            for k in gh_org:
                if orglstr:
                    orglstr += ","
                orglstr += k + ":" + str(gh_org[k])
            spawner.environment['EXTERNAL_GROUPS'] = orglstr
        if gh_name:
            spawner.environment['GITHUB_NAME'] = gh_name
        if gh_token:
            spawner.environment['GITHUB_ACCESS_TOKEN'] = "[secret]"
            self.log.info("Spawned environment: %s", json.dumps(
                spawner.environment, sort_keys=True, indent=4))
            spawner.environment['GITHUB_ACCESS_TOKEN'] = gh_token

    @gen.coroutine
    def _make_options_form(self, spawner):
        # Make options form
        title = os.getenv("LAB_SELECTOR_TITLE") or "Container Image Selector"
        owner = os.getenv("LAB_OWNER") or "lsstsqre"
        repo = os.getenv("LAB_REPO_NAME") or "jld-lab"
        host = os.getenv("LAB_REPO_HOST") or "hub.docker.com"
        scanner = ScanRepo(host=host,
                           owner=owner,
                           name=repo,
                           json=True,
                           )
        scanner.scan()
        lnames, ldescs = scanner.extract_image_info()
        self.log.info("Lab Image Data: %s" % str(lnames))
        if not lnames:
            spawner.singleuser_image_spec = owner + "/" + repo + ":latest"
            spawner.options_form = None
            return
        if len(lnames) == 1:
            imgspec = lnames[0]
            spawner.singleuser_image_spec = imgspec
            spawner.options_form = None
            return
        self.log.info("Lnames: %s" % str(lnames))
        optform = "<label for=\"%s\">%s</label></br>\n" % (title, title)
        for idx, img in enumerate(lnames):
            optform += "      "
            optform += "<input type=\"radio\" name=\"kernel_image\""
            optform += " value=\"%s\">%s<br>\n" % (img, ldescs[idx])
        self.log.info("Options form: %s" % optform)
        spawner.options_form = optform
        return

    @gen.coroutine
    def _get_user_organizations(self, access_token):
        """Get list of orgs user is a member of.  Requires 'read:org'
        token scope.
        """

        http_client = AsyncHTTPClient()
        headers = _api_headers(access_token)
        next_page = "https://%s/user/orgs" % (GITHUB_API)
        orgmap = {}
        while next_page:
            req = HTTPRequest(next_page, method="GET", headers=headers)
            try:
                resp = yield http_client.fetch(req)
            except HTTPError:
                return None
            resp_json = json.loads(resp.body.decode('utf8', 'replace'))
            next_page = next_page_from_links(resp)
            for entry in resp_json:
                # This could result in non-unique groups, if the first 32
                #  characters of the group names are the same.
                normalized_group = entry["login"][:32]
                orgmap[normalized_group] = entry["id"]
        return orgmap

    @gen.coroutine
    def _get_user_email(self, access_token):
        """Determine even private email, if the token has 'user:email'
        scope."""
        http_client = AsyncHTTPClient()
        headers = _api_headers(access_token)
        next_page = "https://%s/user/emails" % (GITHUB_API)
        while next_page:
            req = HTTPRequest(next_page, method="GET", headers=headers)
            resp = yield http_client.fetch(req)
            resp_json = json.loads(resp.body.decode('utf8', 'replace'))
            next_page = next_page_from_links(resp)
            for entry in resp_json:
                if "email" in entry:
                    if "primary" in entry and entry["primary"]:
                        return entry["email"]
        return None


class ScanRepo(object):
    """Class to scan repository and create results.

       Based on:
       https://github.com/shangteus/py-dockerhub/blob/master/dockerhub.py"""

    host = ''
    path = ''
    owner = ''
    name = ''
    data = {}
    debug = False
    json = False
    insecure = False
    sort_field = "comp_ts"
    dailies = 3
    weeklies = 2
    releases = 1

    def __init__(self, host='', path='', owner='', name='',
                 dailies=3, weeklies=2, releases=1,
                 json=False,
                 insecure=False, sort_field="", debug=False):
        if host:
            self.host = host
        if path:
            self.path = path
        if owner:
            self.owner = owner
        if name:
            self.name = name
        if dailies:
            self.dailies = dailies
        if weeklies:
            self.weeklies = weeklies
        if releases:
            self.releases = releases
        if json:
            self.json = json
        protocol = "https"
        if insecure:
            self.insecure = insecure
            protocol = "http"
        if sort_field:
            self.sort_field = sort_field
        if debug:
            self.debug = debug
        if not self.path:
            self.path = "/v2/repositories/" + self.owner + "/" + \
                self.name + "/tags"
        self.url = protocol + "://" + self.host + self.path

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def close(self):
        """Close the session"""
        if self._session:
            self._session.close()

    def extract_image_info(self):
        """Build image name list and image description list"""
        cs = []
        for k in ["daily", "weekly", "release"]:
            cs.extend(self.data[k])
        ldescs = []
        for c in cs:
            tag = c["name"].split(":")[-1]
            if tag[0] == "r":
                rmaj = tag[1:3]
                rmin = tag[3:]
                ld = "Release %s.%s" % (rmaj, rmin)
            elif tag[0] == "w":
                year = tag[1:5]
                week = tag[5:]
                ld = "Weekly %s_%s" % (year, week)
            elif tag[0] == "d":
                year = tag[1:5]
                month = tag[5:7]
                day = tag[7:]
                ld = "Daily %s_%s_%s" % (year, month, day)
            ldescs.append(ld)
        ls = [self.owner + "/" + self.name + ":" + x["name"] for x in cs]
        return ls, ldescs

    def report(self):
        """Print the tag data"""
        if self.json:
            print(json.dumps(self.data, sort_keys=True, indent=4))
        else:
            ls, ldescs = self.extract_image_info()
            ldstr = ",".join(ldescs)
            lstr = ",".join(ls)
            print("# Environment variables for Jupyter Lab containers")
            print("LAB_CONTAINER_NAMES=\'%s\'" % lstr)
            print("LAB_CONTAINER_DESCS=\'%s\'" % ldstr)
            print("export LAB_CONTAINER_NAMES LAB_CONTAINER_DESCS")

    def get_data(self):
        """Return the tag data"""
        return self.data

    def _get_url(self, **kwargs):
        params = None
        resp = None
        url = self.url
        if kwargs:
            params = urllib.parse.urlencode(kwargs)
            url += "?%s" % params
        headers = {"Accept": "application/json"}
        req = urllib.request.Request(url, None, headers)
        resp = urllib.request.urlopen(req)
        page = resp.read()
        return page

    def scan(self):
        url = self.url
        results = []
        page = 1
        while True:
            resp_bytes = self._get_url(page=page)
            resp_text = resp_bytes.decode("utf-8")
            try:
                j = json.loads(resp_text)
            except ValueError:
                raise ValueError("Could not decode '%s' -> '%s' as JSON" %
                                 (url, str(resp_text)))
            results.extend(j["results"])
            if "next" not in j or not j["next"]:
                break
            page = page + 1
        self._reduce_results(results)

    def _reduce_results(self, results):
        sort_field = self.sort_field
        r_candidates = []
        w_candidates = []
        d_candidates = []
        ws = 0
        rs = 1
        for res in results:
            vname = res["name"]
            fc = vname[0]
            res["comp_ts"] = self._convert_time(res["last_updated"])
            if fc == "r":
                r_candidates.append(res)
            if fc == "w":
                w_candidates.append(res)
            if fc == "d":
                d_candidates.append(res)
        r_candidates.sort(key=lambda x: x[sort_field], reverse=True)
        w_candidates.sort(key=lambda x: x[sort_field], reverse=True)
        d_candidates.sort(key=lambda x: x[sort_field], reverse=True)
        r = {}
        r["daily"] = d_candidates[:self.dailies]
        r["weekly"] = w_candidates[:self.weeklies]
        r["release"] = r_candidates[:self.releases]
        for tp in r:
            for v in r[tp]:
                del(v["comp_ts"])
        self.data = r

    def _convert_time(self, ts):
        f = '%Y-%m-%dT%H:%M:%S.%f%Z'
        if ts[-1] == "Z":
            ts = ts[:-1] + "UTC"
        return datetime.datetime.strptime(ts, f)


c.JupyterHub.authenticator_class = LSSTAuth
