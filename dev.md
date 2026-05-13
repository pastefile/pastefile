# Development & test

This document covers:

- Running pastefile locally without packaging it as a container.
- Running the test suite.
- Building and running the dev Docker image.
- Releasing a new version (tag → build → push).

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

You can also run the suite inside the dev Docker container if you want
to validate against the exact Python environment shipped by the image —
see [Running the tests inside the dev container](#running-the-tests-inside-the-dev-container)
below.

## Running the Docker image locally

A dev compose file ([docker-compose.dev.yml](docker-compose.dev.yml)) is
provided. It builds the image from this repo's Dockerfile instead of
pulling from Docker Hub, exposes the service on host port `8080`, and
enables `/ls` for easier testing.

It also **bind-mounts the repo source over `/var/www/pastefile`**, so the
running container always serves the code on your host — no rebuild needed
when you edit a `.py` file. uwsgi caches imported modules, so after editing
restart the workers:

```bash
docker compose -f docker-compose.dev.yml restart
```

Build and start:

```bash
docker compose -f docker-compose.dev.yml up -d --build
```

Smoke test:

```bash
curl -F file=@/etc/hostname http://localhost:8080
curl http://localhost:8080/ls
```

Tear down (data is in `./data-dev/` on the host; delete that directory if
you also want to drop the data):

```bash
docker compose -f docker-compose.dev.yml down
```

### Running the tests inside the dev container

The test suite uses `app.test_client()` (in-process), not real HTTP, so
it doesn't go through nginx/uwsgi — it just needs Python + the deps.
Running it on the host in a venv (see [previous section](#running-the-tests))
is the fastest loop.

If you instead want to run the tests in the exact same Python environment
the production image ships (Debian Trixie, Python 3.13, pinned versions),
do it via `docker exec` against the running dev container. `pytest` is not
shipped in the prod image; install it once:

```bash
docker exec -w /var/www/pastefile pastefile-dev \
    pip install --break-system-packages --ignore-installed pytest
```

`--ignore-installed` is needed because some pytest dependencies (`packaging`,
...) are managed by dpkg and would otherwise refuse to be re-installed.

Then run the suite:

```bash
docker exec -w /var/www/pastefile \
    -e TESTING=TRUE \
    -e PASTEFILE_SETTINGS=./pastefile-test.cfg \
    pastefile-dev \
    pytest pastefile/tests/ -v
```

This works because the dev compose bind-mounts the source — the tests pick
up your local edits without rebuilding.

## Versioning

The version displayed in the UI footer is baked into the image at build
time via a Docker `ARG VERSION` → `ENV PASTEFILE_VERSION` chain. The
Python package reads `os.getenv("PASTEFILE_VERSION", "dev")` from
[pastefile/__init__.py](pastefile/__init__.py).

This works the same in `docker run`, `docker compose`, and Kubernetes
deployments — the env var is part of the image, picked up automatically
unless you explicitly override it in a pod spec.

If you build without passing `--build-arg VERSION=...` (or set
`VERSION=dev` via the dev compose), the footer shows `dev`.

## Releasing a new version

No source file needs to be edited to bump the version. The release flow
is entirely driven by git tags:

**1. Tag the commit you want to release** (annotated tags only — the
release notes live in the tag message):

```bash
git tag -a v1.0.1 -m "v1.0.1 - what changed"
git push origin v1.0.1
```

**2. Build the image from that clean, tagged checkout** (a dirty tree
would produce a `-dirty` suffix in `git describe`):

```bash
docker login

VERSION=$(git describe --tags --always --dirty)
docker build --build-arg VERSION="$VERSION" \
    -t pastefile/pastefile:"$VERSION" \
    -t pastefile/pastefile:latest \
    .
```

**3. Push both the versioned tag and `latest`** to Docker Hub:

```bash
docker push pastefile/pastefile:"$VERSION"
docker push pastefile/pastefile:latest
```

The version baked at build time is what the running container reports
in the UI footer and (eventually) any `/version` endpoint — see
[Versioning](#versioning) above for the mechanism.
