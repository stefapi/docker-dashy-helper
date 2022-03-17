FROM python:3.9-alpine
LABEL maintainer="stephane@apiou.org"

WORKDIR /app/

COPY . .
RUN pip install docker pyyaml

ENTRYPOINT ["python", "start.py"]
CMD ["/app/conf.yml"]
