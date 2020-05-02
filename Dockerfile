FROM python:3-alpine

COPY requirements.txt /tmp/pip-tmp/

RUN apk add libc-dev && apk add gcc && pip --disable-pip-version-check --no-cache-dir install -r /tmp/pip-tmp/requirements.txt \
    && rm -rf /tmp/pip-tmp

COPY *.py /app/

WORKDIR /app
ENTRYPOINT ["python3", "./slack_bot.py"]