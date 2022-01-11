#Docker-Dashy-Helper

A helper container to expose all container as dashy elements.

It takes profit from Traefik configuration to enrich the dashy elements.

this is the offical Traefik docker container.

## Configuration

It reads the same container labels as the Traefik container e.g.

```
traefik.http.routers.r1.rule=Host(`r1.docker.example.com`)
traefik.https.routers.r1.rule=Host(`r1.docker.example.com`)
```
Dashy Urls may be personalised by defining a custom label like this:

````
docker-dashy.url=https://mycontainer.example.com:8080/path/to/site
````
As a fallback, Docker-dashy-helper introspect the container to find exposed ports and build the url based on hostname

Dashy elements are defined with the container Name by default, but you may define a custom label with a container label as:
```
docker-dashy.label=My nice label
```
Dashy groups web sites in the Default Dashy group. You may specify a custom group label e.g.

```
docker-dashy.group=My nice group label
```

Docker-dashy-helper publishes all containers except if the label `docker-dashy.enable=false`. If you define Docker-dashy-helper publishing policy to explicitly publish a container `docker-dashy-.enable` has to be set to true for each container to be published.

Finally, you may restart the dashy docker by marking it with the `docker-dashy.dashy` label.

## Command line arguments

Docker-dashy-helper has only one mandatory parameter which is the file path to the Dashy configuration.

One optional parameter `-d` or `--disable` disables the automatic addition of docker containers to Dashy. You have to put for each container to be added the label `docker-dashy.enable=true`.

Another optional parameter `-n` or `--hostname` specifies the hostname to be used. If not defined, the default hostname used when no URL si given by a label is `localhost`.

## Installing

`docker pull stefapi/docker-dashy-helper`

Currently there are AMD64 based builds.

## Building

Get git repository

`git pull https://github.com/stefapi/docker-dashy-helper`

Build Docker file

`Docker build .`

## Running

To work this needs the following 2 volumes mounting:

` -v /var/run/docker.sock:/var/run/docker.sock`

This allows the container to monitor docker

` -v /path-to-config/conf.yml:/app/conf.yml

And this allows the container to access and modify the Dashy configuration file.

Free Sample:
```
$ docker run -d -v /var/run/docker.sock:/var/run/docker.sock -v /root/dashy_conf.yml:/app/conf.yml stefapi/docker-dashy-helper 
```

## AppArmor

If you are running on system with AppArmor installed you may get errors about not being able to send d-bus messages. To fix this add
`--privileged` to the command line.
