# Docker-Dashy-Helper

A helper container to expose all containers as dashy elements.

It takes profits from Traefik configuration if used to enrich the dashy elements.

Source code is public and found here: [Github Docker-Dashy-Helper](https://github.com/stefapi/docker-dashy-helper).

## TL;DR

It works out of the box just create an empty conf.yml file in the directory you like ( /opt for example) and launch the container:

```
$ touch /opt/conf.yml
$ docker run -d -v /var/run/docker.sock:/var/run/docker.sock -v /opt/conf.yml:/app/conf.yml stefapi/docker-dashy-helper /app/conf.yml 
```

Launch Dashy :

```
$ docker run -d -l 'docker-dashy.dashy' -p 80:80 -v /opt/conf.yml:/app/public/conf.yml lissy93/dashy:latest
```

That's all !

## Configuration

All the configuration is read from container labels (Like Traefik) and the Dashy configuration file is only written if the labels have changed.

### Site definition

These labels are used only in the Dashy container:

`docker-dashy.site` defines the name of the site.

`docker-dashy.comment` defines the description of the site.

`docker-dashy.footer` defines the text displayed in the footer of the Dashy page.

`docker-dashy.options` defines sites options. You define here one or several parameters from the `appConfig` section of the Dashy configuration file. The syntax is: parameter1=`value`,parameter2=`value`. An example of this label is:
```
docker-dashy.options=statusCheck=`true`,faviconApi=`local`,layout=`horizontal`
```

Finally, you may restart the dashy container by marking it with the `docker-dashy.dashy` label. If not marked, the configuration file is written but will not be taken into account by Dashy.

###  Containers definition

These labels are used into containers which are displayed on the Dashy panel.

**Navlinks** are added from the following label: `docker-dashy.navlink.[item].link`.

[Item] is a free text without dot character.

The value of this label is defined with ```Url(`[text]`, `[weblink]`)```.

[Text] is the text displayed in the link button. [weblink] is a standard URL like `https://google.com`

**Items** are defined by the following parameters

`docker-dashy.enable` label conditions the following labels. If set to `true` the labels defined hereunder will be taken into account. if `docker-dashy.enable` is not specified, the default behavior is to enable the container definition unless the `--disable` parameter is specified.

It reads the same container labels as Traefik to define link URL. e.g.

```
traefik.http.routers.r1.rule=Host(`r1.docker.example.com`)
traefik.https.routers.r1.rule=Host(`r1.docker.example.com`)
```
Dashy Urls may be personalised by using the `docker-dashy.url` label like this:

````
docker-dashy.url=https://mycontainer.example.com:8080/path/to/site
````
As a fallback, Docker-dashy-helper introspect the container to find exposed ports and build the url based on hostname (defined with `--hostname` parameter).

Dashy elements are defined with the container Name by default, but you may define a custom label with a container label like:
```
docker-dashy.label=My nice label
```

`docker-dashy.comment` defines the description of the site.

`docker-dashy-icon` defines the icon displayed nearby the site name. For icon definition, please refer to [Dashy icon page](https://github.com/Lissy93/dashy/blob/master/docs/icons.md)

`docker-dashy.color` defines the color of text.

`docker-dashy.bgcolor` defines the color of text background.

`docker-dashy.status` defines the status check of the site.
If the label is defined with empty definition, the site URL will be used to check the status. If the label is defined with an URL, this URL will be used instead.

Defining with the value `internal` will indicate that the check URL is build from the container internal IP address and port.

**IMPORTANT**: with the `internal` parameter you have to check if the Dashy container is able to access the checked IP address. if not the lignt on the dashboard link will be red.

### Groups definition

Items can be grouped.

Dashy groups web sites in the `Default` Dashy group. You may specify a custom group label e.g.

```
docker-dashy.group=My nice group label
```
With `docker-dashy.grp-icon` you define an icon for this group. For icon definition, please refer to [Dashy icon page](https://github.com/Lissy93/dashy/blob/master/docs/icons.md)

With `docker-dashy.grp-prop` you defines properties for the group as per Dashy `displayData` definition. Please refer to the [documentation](https://github.com/Lissy93/dashy/blob/master/docs/configuring.md#sectiondisplaydata-optional).
Each element is defined by a comma separated list of key, value. The syntax is: parameter1=`value`,parameter2=`value`. An example of this label is:
```
docker-dashy.grp-prop=color=`#808080`,collapsed=`true`,sortBy=`most-used`
```

## Command line arguments

Docker-dashy-helper has only one mandatory parameter which is the file path to the Dashy configuration.

Optional parameter `-d` or `--disable` disables the automatic addition of docker containers to Dashy. You have to putthe label `docker-dashy.enable=true` for each container to be added.

Optional parameter `-n` or `--hostname` specifies the hostname to be used. If not defined, the default hostname used when no URL is given by a label is `localhost` followed by port number.

Optional parameter `-l` or `--lang` defines the language to use for Dashy panel. The default value is `en`. Have a look at [Dashy  translations](https://github.com/Lissy93/dashy/tree/master/src/assets/locales)

Optional parameter `-s` or `--size` defines the size of icons. The default value is `medium`. You may specify `small` or `large`.

Optional parameter `-t` or `--theme` definies the theme to use. The default values is `Default`. 

Optional parameter `-k` or `--keep` is used to indicate that the default for size, theme and language will not be forced into the configuration file. Options `-s`, `-t` and `-l` will have no effect.

Optional parameter `-r` or `--reset` defines that the content of configuration file will not ne taken into account at startup. This is useful if you are not sure of the content of this file.

Optional parameter `-f` or `--force` defines that at each loop the file will be erased. Used for parameters debugging purpose.


## Installing

`docker pull stefapi/docker-dashy-helper`

Currently there are AMD64 based builds.

## Building

Get git repository:

`git pull https://github.com/stefapi/docker-dashy-helper`

Build Docker file:

`docker build .`

## Running

You have to attach 2 volumes:

` -v /var/run/docker.sock:/var/run/docker.sock`

` -v /path-to-config/conf.yml:/app/conf.yml

First is used to read docker configuration and the second is used to write Dashy configuration.

Free Sample of container lauch:
```
$ docker run -d -v /var/run/docker.sock:/var/run/docker.sock -v /opt/dashy_conf.yml:/app/conf.yml stefapi/docker-dashy-helper -l en -s large /app/conf.yml 
```

you start your Dashy container with this docker command:
```
$ docker run -d --name dashy -l 'docker-dashy.url=https://dashy.local' -l 'docker-dashy.dashy' -p 5000:80 -v /opt/dashy_conf.yml:/app/public/conf.yml lissy93/dashy:latest
```


then, you start a client container with this command (example given for portainer):
```
$ docker run -d --name=portainer -l 'docker-dashy.url=https://portainer.local' -l 'docker-dashy.icon=si-portainer' -p 9050:9000 -v /var/run/docker.sock:/var/run/docker.sock -v portainer_data:/data portainer/portainer-ce
```

## AppArmor

If you are running on system with AppArmor installed you may get errors about not being able to send d-bus messages. To fix this add
`--privileged` to the command line.
