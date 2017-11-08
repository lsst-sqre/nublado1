"""
Create the options form from our environment variables.
"""

import os


class ScanRepo(object):
    """Class to scan repository and create results.

       Based on:
       https://github.com/shangteus/py-dockerhub/blob/master/dockerhub.py"""

    host = ''
    path = '/'
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

    def __init__(self, host='', path='/', owner='', name='',
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
        self.url = protocol + "://" + self.host + self.path

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def close(self):
        """Close the session"""
        if self._session:
            self._session.close()

    def report(self):
        """Print the tag data"""
        if self.json:
            print(json.dumps(self.data, sort_keys=True, indent=4))
        else:
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
            ldstr = ",".join(ldescs)
            ls = [self.owner + "/" + self.name + ":" + x["name"] for x in cs]
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
        debug = self.debug
        results = []
        page = 1
        while True:
            resp_bytes = self._get_url(page=page)
            resp_text = resp_bytes.decode("utf-8")
            j = json.loads(resp_text)
            results.extend(j["results"])
            if "next" not in j or not j["next"]:
                break
            page = page + 1
        self._debuglog("Tags: %s" % json.dumps(results, indent=4))
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
        self._debuglog("Converting time %s" % ts)
        if ts[-1] == "Z":
            ts = ts[:-1] + "UTC"
        return datetime.datetime.strptime(ts, f)

    def _debuglog(self, *args, **kwargs):
        if not self.debug:
            return
        print(*args, file=sys.stderr, **kwargs)


def _make_options_form():
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
    labdata = scanner.data
    imgspec = {"kernel_image": labdata["daily"] + labdata["weekly"] +
               labdata["release"]}
    klist = imgspec["kernel_image"]
    if not klist:
        imgspec = owner + "/" + repo + ":latest"
        return None
    elif len(klist) == 1:
        imgspec = klist[0]
    else:
        imgspec = klist
    if type(imgspec) is not list:
        c.LSSTSpawner.singleuser_image_spec = imgspec
        c.LSSTSpawner.options_form = None
        return None
    optform = "<label for=\"%s\">%s</label></br>\n" % (title, title)
    for img in imgspec:
        optform += "      "
        optform += "<input type=\"radio\" name=\"kernel_image\""
        optform += " value=\"%s\">%s<br>\n" % (img, img)
    c.LSSTSpawner.options_form = optform
