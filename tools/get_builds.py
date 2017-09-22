#!/usr/bin/env python3
"""Scan Docker repository for most recent weekly and release builds.
"""

import argparse
import datetime
import json
import sys
import urllib.parse
import urllib.request
# Yes, Requests would be nicer but I'm keeping it to the standard lib.


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


def parse_args():
    """Parse command-line arguments"""
    parser = argparse.ArgumentParser(description="Scan Docker repo.")
    parser.add_argument("-d", "--debug", action="store_true",
                        help="enable debugging")
    parser.add_argument("-j", "--json",
                        action="store_true",
                        help="output as JSON, not environmental strings")
    parser.add_argument("-r", "--repo", "--repository",
                        help="repository host [hub.docker.com]",
                        default="hub.docker.com")
    parser.add_argument("-o", "--owner", "--organization", "--org",
                        help="repository owner [lsstsqre]",
                        default="lsstsqre")
    parser.add_argument("-n", "--name",
                        help="repository name [jld-lab]",
                        default="jld-lab")
    parser.add_argument("-q", "--dailies", "--daily", "--quotidian", type=int,
                        help="# of daily builds to keep [3]",
                        default=3)
    parser.add_argument("-w", "--weeklies", "--weekly", type=int,
                        help="# of weekly builds to keep [2]",
                        default=2)
    parser.add_argument("-b", "--releases", "--release", type=int,
                        help="# of release builds to keep [1]",
                        default=1)
    parser.add_argument("-i", "--insecure", "--no-tls", "--no-ssl",
                        help="Do not use TLS to connect [False]",
                        type=bool,
                        default=False)
    parser.add_argument("-s", "--sort", "--sort-field", "--sort-by",
                        help="Field to sort results by [comp_ts]",
                        default="comp_ts")
    results = parser.parse_args()
    results.path = "/v2/repositories/" + results.owner + "/" + \
        results.name + "/tags"
    return results


def main():
    """Primary entry point
    """
    args = parse_args()
    repo = ScanRepo(host=args.repo, path=args.path,
                    owner=args.owner, name=args.name,
                    dailies=args.dailies, weeklies=args.weeklies,
                    releases=args.releases,
                    json=args.json, insecure=args.insecure,
                    sort_field=args.sort, debug=args.debug)
    repo.scan()
    repo.report()


if __name__ == "__main__":
    main()
