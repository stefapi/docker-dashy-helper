FROM python:slim
LABEL maintainer="stephane@apiou.org"

WORKDIR /app/

COPY . .

CMD ["python", "start.py", "/app/conf.yml"]
