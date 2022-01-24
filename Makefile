docker:
	docker build --tag stefapi/docker-dashy-helper:latest --platform linux/amd64 .
	docker push stefapi/docker-dashy-helper:latest
