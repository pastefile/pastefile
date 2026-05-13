Pastefile
=========

Little daemon written with python flask for sharing any files quickly via http
------------------------------------------------------------------------------

- [Installation](#installation)
- [Options](#options)
- [Usage](#usage)
- [Extra](#extra)

See [dev.md](dev.md) for local development and how to run the tests.


# Installation

The supported production deployment is the bundled Docker image. It packages
nginx + uwsgi + pastefile and is configured through environment variables or
an optional config file (see [Options](#options)).

A ready-to-use compose file ships in this repo:

```bash
git clone https://github.com/pastefile/pastefile.git
cd pastefile
docker compose up -d
```

This pulls `pastefile/pastefile:latest` from Docker Hub, exposes nginx on
host port `80`, and persists uploaded files and the json DB in `./data/`
on the host (next to the compose file).

> The host data directory is created on first run; it must be writable by
> the in-container uwsgi process (uid 33 / gid 33 = `www-data`). If you
> see permission errors, run once: `sudo chown -R 33:33 ./data`.

## Customizing

[docker-compose.yml](docker-compose.yml) ships with every common tunable
commented out, ready to uncomment. Typical things you'll want to change:

- The host port mapping (`ports:` section).
- Application config (`EXPIRE`, `DISABLED_FEATURE`, ...).
- Tuning for large uploads (`MAX_FILE_SIZE`, `UWSGI_PROCESSES`, ...).
- Mounting a config file (set the volume and `PASTEFILE_SETTINGS`).

`DISABLED_FEATURE` is comma-separated; allowed values are `ls` and `delete`.
Its default is `ls` (so `/ls` is off out of the box) — set
`DISABLED_FEATURE: ""` in the compose file to enable it.

After editing the compose file, re-apply:

```bash
docker compose up -d
```


# Options

Every option below can be set in two ways:

1. **Environment variable**, e.g. `docker run -e EXPIRE=3600 ...`.
2. **Config file** pointed to by `PASTEFILE_SETTINGS` (e.g. `/etc/pastefile.cfg`).

Config-file values **take precedence** over env vars for the keys they define.
Env vars take precedence over the built-in defaults.

Config file syntax is `KEY = VALUE`, the key in uppercase and string values
quoted with `"..."` (see [pastefile.cfg.sample](pastefile.cfg.sample)).

## Application config

| Parameter          | Default                                  | Usage                                                                                  |
|--------------------|------------------------------------------|----------------------------------------------------------------------------------------|
| `UPLOAD_FOLDER`    | `/opt/pastefile/files`                   | Where uploaded files are stored.                                                       |
| `FILE_LIST`        | `/opt/pastefile/uploaded_files_jsondb`   | The file that acts as the DB (jsondb).                                                 |
| `TMP_FOLDER`       | `/opt/pastefile/tmp`                     | Where files are buffered during the transfer (before being moved to `UPLOAD_FOLDER`).  |
| `EXPIRE`           | `86400` (1 day)                          | How long files are retained, in seconds.                                               |
| `LOG`              | `/opt/pastefile/pastefile.log`           | Path to the log file.                                                                  |
| `DISABLED_FEATURE` | `ls`                                     | Comma-separated list of disabled endpoints. Allowed: `delete`, `ls`. ⚠️ `/ls` is **disabled by default**; pass `DISABLED_FEATURE=""` to enable it. |

> **Notes**
> - The upload directory and the db file must be writable by the uwsgi
>   process (uid `33` / gid `33` in the Docker image).
> - **Performance**: pastefile uses `shutil.move`. Put `TMP_FOLDER` and
>   `UPLOAD_FOLDER` on the same filesystem so the move stays a rename
>   instead of a copy.

## Docker entrypoint environment

These tune the bundled nginx + uwsgi stack inside the container. They have no
config-file equivalent — set them with `docker run -e ...`.

| Variable                  | Default       | Usage                                                                                          |
|---------------------------|---------------|------------------------------------------------------------------------------------------------|
| `MAX_FILE_SIZE`           | `1G`          | Maximum request body size accepted by nginx. Same syntax as nginx `client_max_body_size`: `100M`, `2G`, etc. Requests above this get a `413 Request Entity Too Large`. |
| `UWSGI_PROCESSES`         | `4`           | Number of uwsgi worker processes. Each upload holds a worker until completion, so this caps concurrent uploads. Rule of thumb: ~2× the number of CPU cores. No `auto` mode (unlike nginx). |
| `UWSGI_CONNECT_TIMEOUT`   | `60s`         | nginx-to-uwsgi connect timeout.                                                                |
| `UWSGI_READ_TIMEOUT`      | `60s`         | Timeout between two successive reads from uwsgi. Bump if uploads of large files time out.      |
| `UWSGI_SEND_TIMEOUT`      | `60s`         | Timeout between two successive writes to uwsgi. Same remark as `UWSGI_READ_TIMEOUT`.           |
| `NGINX_WORKER_PROCESSES`  | `auto`        | nginx `worker_processes`. `auto` = one per CPU core.                                           |
| `NGINX_WORKER_CONNECTIONS`| `1024`        | nginx `worker_connections` per worker.                                                         |
| `NGINX_KEEPALIVE_TIMEOUT` | `1`           | nginx `keepalive_timeout` (seconds).                                                           |
| `NGINX_DEFAULT_PORT`      | `80`          | Port the nginx vhost listens on inside the container (the `-p host:container` mapping must match). |
| `NGINX_APP_NAME`          | `pastefile`   | Server name used in the nginx vhost.                                                           |

> **Tuning for large uploads**
> If you accept files larger than the default `1G`, you typically need to
> bump three things together:
> - `MAX_FILE_SIZE` (otherwise nginx 413s the request),
> - `UWSGI_READ_TIMEOUT` / `UWSGI_SEND_TIMEOUT` (otherwise nginx aborts a slow upload),
> - `UWSGI_PROCESSES` (each in-flight upload occupies a worker for its whole duration).


# Usage

The examples below assume the container is reachable at `http://localhost`;
replace it with your own host or domain.

The upload endpoint returns a URL whose last path component is the file's
**md5 hash** — that's the `<id>` referenced in the URLs below.

Upload a file:
```bash
curl -F file=@</path/to/the/file> http://localhost
```

Upload a file with **burn after read** — the file is deleted from disk the
first time it is fetched, so subsequent requests return `404`:
```bash
curl -F file=@</path/to/the/file> -F burn=true http://localhost
```

View all uploaded files (⚠️ this endpoint is **disabled by default**; see
`DISABLED_FEATURE` in [Options](#options) to enable it):
```bash
curl http://localhost/ls
```

Get infos about one file:
```bash
curl http://localhost/<id>/infos
```

Get a file:
```bash
curl -JO http://localhost/<id>
```

When the same URL is opened in a browser, pastefile decides between **inline**
display (the file is rendered directly in the browser tab) and **attachment**
(the browser triggers a "save as" download) based on the file's MIME type:

- **Inline** for `image/*`, `text/*`, `audio/*`, `video/*`, `application/pdf`, `application/json`.
- **Attachment** for anything else, and always for CLI clients (`curl`, `wget`, `httpie`).

In both cases the original filename (with its extension) is preserved.

Delete a file:
```bash
curl -XDELETE http://localhost/<id>
```

You can add this to your `.bashrc` for convenience:
```bash
pastefile() { curl -F file=@"$1" http://localhost; }
```
and then:
```bash
pastefile /my/file
```


# Extra

Simple script to take a screenshot of a selected region of the screen and
upload it to pastefile. The pastefile link is automatically copied to your
clipboard.

```bash
#!/bin/bash

# require :
# apt-get install imagemagick xsel libnotify-bin

filename=$(mktemp --suffix=_screenshot.png)
# Take the screenshot
import $filename

# Upload the file on pastefile
url=$(curl -F "file=@${filename}" http://localhost)
if [ "$?" = "0" ]; then
    notify-send "image uploaded! $url"

    # Add file to all clipboards
    echo -n "$url"|xsel -i -p
    echo -n "$url"|xsel -i -s
    echo -n "$url"|xsel -i -b
    echo "$url" >> /tmp/import.log
else
    notify-send --urgency=critical "Upload failed."
fi
```
