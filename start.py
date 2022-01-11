#!/bin/env python3

import sys
import os
import logging
import logging.handlers
import syslog
import re
import signal
import functools

from argparse import ArgumentParser, ArgumentTypeError
from time import sleep
import docker
import yaml

log = logging.getLogger("Traefik to Dashy");

def handle_signals(signum, frame):
    signame = next(v for v, k in signal.__dict__.items() if k == signum)
    log.info("Exiting on %s...", signame)
    os._exit(0)

def main():
    parser = ArgumentParser(description="Helper container which updates Dashy configuration based on Docker or Traefik configuration")
    parser.add_argument('-d', '--disable', help='Containers are not automatically added', action='store_true')
    parser.add_argument('-n', '--hostname', help='Specify a hostname for the default URL', nargs='?', default='localhost', metavar='<hostname>')
    parser.add_argument("yamlfile",help = "File containing the yaml configuration", nargs=1)

    res= parser.parse_args(sys.argv[1:])
    yamlfile =res.yamlfile[0]
    enable_default = not res.disable
    hostname = res.hostname

    handler = logging.StreamHandler(sys.stderr)
    format_string = "%(levelname)s: %(message)s"

    handler.setFormatter(logging.Formatter(format_string))
    logging.getLogger().addHandler(handler)

    log.setLevel(logging.INFO)

    signal.signal(signal.SIGTERM, functools.partial(handle_signals))
    signal.signal(signal.SIGINT, functools.partial(handle_signals))
    signal.signal(signal.SIGQUIT, functools.partial(handle_signals))

    while True:
        client = docker.from_env()

        dashy_grp = {}
        restart_id = 0
        r = re.compile("traefik\.https?\.routers\..*\.rule")
        hst = re.compile("Host\(`(.*)`\)")
        updated = False
        for container in client.containers.list():
            labels = container.labels
            if "docker-dashy.dashy" in labels:
                restart_id = container.id
                restart_name = container.name
            if (enable_default == False and "docker-dashy.enable" in labels and labels["docker-dashy.enable"].tolower == "true") or (enable_default == True and not ("docker-dashy.enable" in labels and labels["docker-dashy.enable"].tolower == "false")):
                res = list(filter(r.match, list(labels.keys())))
                url=''
                if len(container.ports) > 0:
                    for portitem, portlist in container.ports.items():
                        if portlist is not None:
                            url = 'http://{}:{}'.format(hostname, portlist[0]["HostPort"])
                            break

                if len(res) > 0:
                    matched = hst.search(labels[res[0]])
                    if "https" in res[0]:
                        url = "https://"+matched.group(1)
                    else:
                        url = "http://"+matched.group(1)
                lbl = container.name
                if "docker-dashy.url" in labels:
                    url = labels["docker-dashy.label"]
                if "docker-dashy.label" in labels:
                    lbl = labels["docker-dashy.label"]
                grp = "Default"
                if "docker-dashy.group" in labels:
                    grp = labels["docker-dashy.group"]
                if grp not in dashy_grp:
                    dashy_grp[grp] = []
                if url != "":
                    dashy_grp[grp].append((lbl, url))
        with open(yamlfile, "r") as stream:
            try:
                yml_tree = yaml.safe_load(stream)
            except yaml.YAMLError as exc:
                print(exc)
                return
        if 'sections' in yml_tree:
            sections = yml_tree['sections']
        else:
            sections = []
        for (grp, grp_lst) in dashy_grp.items():
            found_section = False
            for section in sections:
                if section["name"] == grp:
                    found_section = True
                    items = section["items"]
            if found_section == False:
                updated = True
                items = []
                new_section = {"name": grp,
                               "displayData": {"sortBy": "default", "rows": 1, "cols": 1, "collapsed": False,
                                               "hideForGuests": False},
                               "items": items}
                sections.append(new_section)
            for (lbl, url) in grp_lst:
                item_found = False
                for item in items:
                    if item["title"] == lbl:
                        if item["url"] != url:
                            updated= True
                        item["url"] = url
                        item_found = True
                if item_found == False:
                    updated = True
                    new_item = {"title": lbl, "url": url, "target": "newtab", "statusCheck": False}
                    items.append(new_item)
        if updated:
            with open(yamlfile, "w") as stream:
                yaml.dump(yml_tree, stream)
            log.info("All portal items published")
        if restart_id != 0 and updated:
            #client.container.restart(restart_id)
            client.containers.get(restart_id).restart()
            log.info("restarted " + restart_name)
        sleep(1)

if __name__ == "__main__":
    main()
