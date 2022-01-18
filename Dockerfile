FROM python:slim
LABEL maintainer="stephane@apiou.org"

RUN \
  pip install -U pip

WORKDIR /app/

COPY . .
RUN pip install docker pyyaml

ENTRYPOINT ["python", "start.py"]
CMD ["/app/conf.yml"]
