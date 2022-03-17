#!/bin/env python3

import sys
import os
import logging
import logging.handlers
import re
import signal
import functools

from argparse import ArgumentParser
from time import sleep
import docker
import yaml
import collections.abc


# Default Time-to-Live for mDNS records, in seconds...
DEFAULT_DASHY_WAIT = 10

log = logging.getLogger("Traefik to Dashy")

def update(d, u):
    updated = False
    for k, v in u.items():
        if k in d and isinstance(v, collections.abc.Mapping) and isinstance(d[k],collections.abc.Mapping):
            updated |= update(d[k], v)
        else:
            if k not in d or d[k] != v:
                updated = True
                d[k] = v
    return updated

def handle_signals(signum, frame):
    signame = next(v for v, k in signal.__dict__.items() if k == signum)
    log.info("Exiting on %s...", signame)
    os._exit(0)


def main():
    parser = ArgumentParser(
        description="Helper container which updates Dashy configuration based on Docker or Traefik configuration")
    parser.add_argument('-d', '--disable', help='Containers are not automatically added', action='store_true')
    parser.add_argument('-n', '--hostname', help='Specify a hostname for the default URL', default='localhost', metavar='<hostname>')
    parser.add_argument('-l', '--lang', help='Specify language for the site', default='en', metavar='<lang>')
    parser.add_argument('-s', '--size', help='Specify the size of icons', default='medium', metavar='<lang>')
    parser.add_argument('-t', '--theme', help='Specify theming for the site', default='Default', metavar='<lang>')
    parser.add_argument('-k', '--keep', help='dont use default and keep the content of yaml file for language, icon size and theme', action='store_true')
    parser.add_argument('-r', '--reset', help='Forget content of yaml file at startup', action='store_true')
    parser.add_argument('-f', '--force', help='Forget content of yaml file at each loop', action='store_true')
    parser.add_argument('-w', '--wait', help='waiting time between each analysis loop', default=DEFAULT_DASHY_WAIT, metavar='<seconds>')
    parser.add_argument("yamlfile", help="File containing the yaml configuration. If empty will be created", nargs=1)

    res = parser.parse_args(sys.argv[1:])
    yamlfile = res.yamlfile[0]
    enable_default = not res.disable
    hostname = res.hostname
    lang = res.lang
    size = res.size
    theme = res.theme
    keep = res.keep
    reset = res.reset or res.force
    force = res.force
    refresh_rate = int(res.wait)

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
        dashy_prop = {}
        restart_id = 0
        sitename = ""
        sitecomment = ""
        sitefooter = ""
        siteoptions = ""
        yml_tree = None

        r = re.compile("^traefik\.https?\.routers\..+\.rule$")
        n = re.compile("^docker-dashy\.navlink\..+\.link$")
        hst = re.compile("Host\(\s*`([^`]*)`.*?\)")
        navlink = re.compile("Url\(\s*`(.+)`\s*,\s*`(.+)`\s*\)")
        options = re.compile("(.+?)=`(.+?)`")
        updated = False
        try:
            with open(yamlfile, "r") as stream:
                try:
                    yml_tree = yaml.safe_load(stream)
                except yaml.YAMLError as exc:
                    print(exc)
        except IOError as exc:
            print(exc)
            print("Starting from empty file")
        if yml_tree is None:
            yml_tree = {}
        if reset:
            yml_tree = {}
            if not force:
                print("Starting from empty file")
                reset = False

        # create or get root branches
        if 'pageInfo' in yml_tree and yml_tree["pageInfo"] is not None:
            pageinfo = yml_tree['pageInfo']
        else:
            updated = True
            pageinfo = {}
            yml_tree['pageInfo'] = pageinfo

        if "navLinks" in pageinfo and pageinfo["navLinks"] is not None:
            navlinks = pageinfo["navLinks"]
        else:
            updated = True
            navlinks = []
            pageinfo["navLinks"] = navlinks

        if 'appConfig' in yml_tree and yml_tree['appConfig'] is not None:
            appconfig = yml_tree['appConfig']
        else:
            updated = True
            appconfig = {}
            yml_tree['appConfig'] = appconfig

        if 'sections' in yml_tree and yml_tree['sections'] is not None:
            sections = yml_tree['sections']
        else:
            updated = True
            sections = []
            yml_tree['sections'] = sections

        for container in client.containers.list():
            labels = container.labels

            #  Sitename the content of docker-dashy.site label fallback on the name of docker container
            # Comment is the content of docker-dashy.comment label
            # Footer is the content of docker-dashy.footer label
            if "docker-dashy.dashy" in labels:
                restart_id = container.id
                restart_name = container.name
                res = list(filter(r.fullmatch, list(labels.keys())))
                sitename = restart_name
                if "docker-dashy.site" in labels:
                    sitename = labels["docker-dashy.site"]
                elif len(res) > 0:
                    matched = hst.match(labels[res[0]])
                    if matched is not None:
                        sitename = matched.group(1)
                if "docker-dashy.comment" in labels:
                    sitecomment = labels["docker-dashy.comment"]
                if "docker-dashy.footer" in labels:
                    sitefooter = labels["docker-dashy.footer"]
                if "docker-dashy.options" in labels:
                    siteoptions = labels["docker-dashy.options"]

            # Navlinks update. No more than 6 navlinks. We update based on identity on url or title otherwise, we add the link
            res = list(filter(n.match, list(labels.keys())))
            if len(res) > 0:
                for res_item in res:
                    matched = navlink.fullmatch(labels[res_item])
                    if matched is not None:
                        url_title = matched.group(1)
                        url_link = matched.group(2)
                        found_link = None
                        for link in navlinks:
                            if link["title"] == url_title or link["path"] == url_link:
                                found_link = link
                        if found_link is not None:
                            if not (found_link["title"] == url_title and found_link["path"] == url_link):
                                updated = True
                                found_link["title"] = url_title
                                found_link["path"] = url_link
                        elif len(navlinks) < 6:
                            updated = True
                            navlnk = {}
                            navlnk["title"] = url_title
                            navlnk["path"] = url_link
                            navlinks.append(navlnk)

            # Container links are treated if docker-dashy.enable is True.
            # For this containers, we set:
            #   a label item base on docker-dashy.label. the container name is used as a fallback
            #   an Url based on docker-dashy.url. The Host defined in traefik.http.routers...rule is used as fallback and as a last resort we use the hostname and docker portnumber with http
            #   a group based on docker-dashy.group. If not defined, the group is "Default"
            #   Optional: properties for a group based on docker-dashy.grp-prop. Syntax is property1=`...`,property2=`...` ... where property is a Field of displayData section of Dashy
            #   Optional: an icon for the group based on docker-dashy.grp-icon
            #   Optional: an icon for the URL based on docker-dashy.icon
            #   Optional: a description for the URL based on docker-dashy.comment
            #   Optional: a status check based on docker-dashy.status with if defined empty uses the URL.
            #   Optional: a color for the URL based on docker-dashy.color
            #   Optional: a background color for the URL based on docker-dashy.bgcolor
            if (enable_default == False and "docker-dashy.enable" in labels and labels[
                "docker-dashy.enable"].lower() == "true") or (enable_default == True and not (
                    "docker-dashy.enable" in labels and labels["docker-dashy.enable"].lower() == "false")):
                res = list(filter(r.match, list(labels.keys())))
                url = ''
                if len(container.ports) > 0:
                    for portitem, portlist in container.ports.items():
                        if portlist is not None:
                            url = 'http://{}:{}'.format(hostname, portlist[0]["HostPort"])
                            break

                if len(res) > 0:
                    matched = hst.fullmatch(labels[res[0]])
                    if matched is not None:
                        if "https" in res[0]:
                            url = "https://" + matched.group(1)
                        else:
                            url = "http://" + matched.group(1)
                if "docker-dashy.url" in labels:
                    url = labels["docker-dashy.url"]
                lbl = container.name
                if "docker-dashy.label" in labels:
                    lbl = labels["docker-dashy.label"]
                item = {"title": lbl, "url": url}
                if "docker-dashy.comment" in labels:
                    item["description"] = labels["docker-dashy.comment"]
                if "docker-dashy.icon" in labels:
                    item["icon"] = labels["docker-dashy.icon"]
                if "docker-dashy.status" in labels:
                    item["statusCheck"] = 'true'
                    lnk = labels["docker-dashy.status"]
                    if "http" in lnk:
                        item["statusCheckUrl"] =lnk
                        if "https" not in lnk:
                            item["statusCheckAllowInsecure"] = "true"
                    elif "internal" in lnk:
                        port = None
                        if len(container.ports) > 0:
                            for portitem in container.ports.keys():
                                if "/tcp" in portitem:
                                    match = re.fullmatch("^(.*)/tcp$", portitem)
                                    if match is not None:
                                        port = match.group(1)
                                        break
                        if port is not None:
                            if container.attrs["NetworkSettings"]["IPAddress"] == "":
                                nets = container.attrs["NetworkSettings"][ "Networks"]
                                for key, value in nets.items():
                                    if value["IPAddress"] != "":
                                        item["statusCheckUrl"] = "http://" + value[ "IPAddress"] + ":" + port
                                        item["statusCheckAllowInsecure"] = "true"
                                        break;
                            else:
                                item["statusCheckUrl"] = "http://"+container.attrs["NetworkSettings"]["IPAddress"]+":"+port
                                item["statusCheckAllowInsecure"] = "true"
                    else:
                        if "https" not in url:
                            item["statusCheckAllowInsecure"] = "true"
                if "docker-dashy.color" in labels:
                    item["color"] = labels["docker-dashy.color"]
                if "docker-dashy.bgcolor" in labels:
                    item["bgcolor"] = labels["docker-dashy.bgcolor"]
                grp = "Default"
                if "docker-dashy.group" in labels:
                    grp = labels["docker-dashy.group"]
                properties = {}
                if "docker-dashy.grp-icon" in labels:
                    properties["icon"] = labels["docker-dashy.grp-icon"]
                if "docker-dashy.grp-prop" in labels:
                    props = labels["docker-dashy.grp-prop"]
                    propslist = [ s.strip() for s in re.split('(?<=`)\s*,\s*(?=[^,]+?=\s*`)',props)]
                    displayData = {}
                    for prop in propslist:
                        match = options.match(prop)
                        if match is None:
                            print("docker-dashy.grp-prop is malformed: " + labels["docker-dashy.grp-prop"])
                        else:
                            displayData[match[1]] = match[2]
                    if len(displayData) > 0:
                        properties["displayData"]= displayData
                if url != "":
                    if grp not in dashy_grp:
                        dashy_grp[grp] = {}
                    dashy_grp[grp][lbl]= item
                    if grp in dashy_prop:
                        update(dashy_prop[grp],properties)
                    else:
                        dashy_prop[grp] = properties

        # Update YML structure
        # Create pageinfo based on information collected before
        if sitename != "":
            if "title" not in pageinfo or pageinfo["title"] != sitename:
                updated = True
                pageinfo["title"] = sitename
        elif "title" not in pageinfo:
            updated = True
            pageinfo["title"] = "Dashy"
        if sitecomment != "":
            if "description" not in pageinfo  or pageinfo["description"] != sitecomment:
                updated = True
                pageinfo["description"] = sitecomment
        elif "description" not in pageinfo:
            updated = True
            pageinfo["description"] = "Dashy Board"
        if sitefooter != "":
            if "footerText" not in pageinfo or pageinfo["footerText"] != sitefooter:
                updated = True
                pageinfo["footerText"] = sitefooter


        # Update appConfig
        if keep == False:
            if "language" not in appconfig or appconfig["language"] != lang:
                updated = True
                appconfig["language"] = lang
            if "iconSize" not in appconfig or appconfig["iconSize"] != size:
                updated = True
                appconfig["iconSize"] = size
            if "theme" not in appconfig or appconfig["theme"] != theme:
                updated = True
                appconfig["theme"] = theme
        if siteoptions != "":
            props = options.fullmatch(siteoptions)
            if props is None or len(props.groups()) % 2 != 0:
                    print("docker-dashy.grp-prop is malformed: " + labels["docker-dashy.grp-prop"])
            else:
                for key, val in zip(*[iter(props.groups())] * 2):
                    if key not in appconfig or appconfig[key] != val:
                        updated = True
                        appconfig[key]  = val

        # Treat sections and URLs
        for (grp, grp_lst) in dashy_grp.items():
            found_section = None
            for section in sections:
                if section["name"] == grp:
                    found_section = section
                    items = section["items"]
            if found_section == None:
                updated = True
                items = []
                found_section = {"name": grp,
                               "items": items}
                sections.append(found_section)
            if grp in dashy_prop:
                for key, value in dashy_prop[grp].items():
                    if key not in found_section or found_section[key] != value:
                        if key != "displayData":
                            updated= True
                            found_section[key] = value
                        else:
                            if key not in found_section:
                                displayData = {}
                                found_section[key] = displayData
                                updated=True
                            else:
                                displayData = found_section[key]
                            updated |= update(displayData, value)
            for lbl, props in grp_lst.items():
                item_found = None
                for item in items:
                    if item["title"] == lbl:
                        item_found = item
                        break;
                if item_found is None:
                    updated = True
                    item = {"title": lbl}
                    items.append(item)
                for key, value in props.items():
                    if key not in item or item[key] != value:
                        updated = True
                        item[key] = value

        # if something was updated write it in configuration file
        if updated:
            with open(yamlfile, "w") as stream:
                yaml.dump(yml_tree, stream)
            log.info("All portal items published")
        if restart_id != 0 and updated:
            # client.container.restart(restart_id)
            client.containers.get(restart_id).restart()
            log.info("restarted " + restart_name)
        sleep(refresh_rate)


if __name__ == "__main__":
    main()
