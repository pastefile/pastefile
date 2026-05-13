# Development & test

This document covers:

- Running pastefile locally without packaging it as a container.
- Running the test suite.
- Building and publishing the Docker image.

The supported production path is the pre-built Docker image (see
[README.md](README.md)).

## Quick run for test purpose

A small `pastefile-run.py` script is provided to launch pastefile in a
Flask development server, without nginx/uwsgi.

Recommended setup on Debian Trixie (Python 3.13) — uses a virtualenv to
avoid PEP 668 (`externally-managed-environment`):

```bash
apt-get install -y git python3-dev python3-pip python3-venv libmagic1
git clone https://github.com/pastefile/pastefile.git
cd pastefile
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp pastefile.cfg.sample pastefile.cfg
# Edit pastefile.cfg to adjust the directories
.venv/bin/python pastefile-run.py -c $PWD/pastefile.cfg
```

The dev server listens on `0.0.0.0:DEBUG_PORT` (default `5000`). This port
is only used by `pastefile-run.py`; in the Docker image nginx listens on
`NGINX_DEFAULT_PORT` instead and `DEBUG_PORT` is ignored.

## Running the tests

Install the extra test dependencies into the same venv:

```bash
.venv/bin/pip install -r test-requirements.txt
```

Run the test suite with `pytest`. The application config file is loaded from
the `PASTEFILE_SETTINGS` env var; for tests we use `pastefile-test.cfg`
(uses `./tests/` as the storage root, cleaned between tests).

```bash
TESTING=TRUE PASTEFILE_SETTINGS=./pastefile-test.cfg \
    .venv/bin/pytest pastefile/tests/ -v
```

Or via tox (runs the tests and `flake8`):

```bash
.venv/bin/tox
```

## Running the Docker image locally

A dev compose file ([docker-compose.dev.yml](docker-compose.dev.yml)) is
provided. It builds the image from this repo's Dockerfile instead of
pulling from Docker Hub, exposes the service on host port `8080` so it
does not clash with a prod instance, and enables `/ls` for easier testing.

Build and start:

```bash
docker compose -f docker-compose.dev.yml up -d --build
```

Smoke test:

```bash
curl -F file=@/etc/hostname http://localhost:8080
curl http://localhost:8080/ls
```

Tear down (keeps the data volume) or with `-v` (also drops the data):

```bash
docker compose -f docker-compose.dev.yml down
docker compose -f docker-compose.dev.yml down -v
```

## Publishing the image to Docker Hub

After building locally and testing, retag and push to the registry:

```bash
docker login

# Latest
docker tag pastefile/pastefile:local pastefile/pastefile:latest
docker push pastefile/pastefile:latest

# Versioned release
docker tag pastefile/pastefile:local pastefile/pastefile:1.0
docker push pastefile/pastefile:1.0
```
