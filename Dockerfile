# syntax=docker/dockerfile:1
FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN groupadd --system flaskapp \
    && useradd --system --gid flaskapp --home-dir /app flaskapp

COPY requirements.txt requirements-docker.txt ./
RUN python -m pip install --upgrade pip \
    && python -m pip install -r requirements-docker.txt

COPY --chown=flaskapp:flaskapp . .
COPY --chown=flaskapp:flaskapp docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod 0755 /usr/local/bin/docker-entrypoint.sh

USER flaskapp
EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:5000/health', timeout=3)" || exit 1

ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["gunicorn","--bind","0.0.0.0:5000","--workers","2","--threads","4","--timeout","30","--access-logfile","-","--error-logfile","-","app:app"]
