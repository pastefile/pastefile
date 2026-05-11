FROM debian:trixie
LABEL maintainer="Guillaume Abrioux <guillaume@abrioux.info>"

COPY ./ /var/www/pastefile
RUN apt-get update && apt-get install -y nginx-full gettext-base python3-pip python3-dev gcc libmagic1 && apt-get clean
RUN pip3 install --break-system-packages --no-cache-dir -r /var/www/pastefile/requirements.txt
RUN mkdir /opt/pastefile && mkdir -p /opt/pastefile/files/ /opt/pastefile/tmp
RUN chown -R www-data:www-data /opt/pastefile

COPY ./extra/Docker/configs/nginx.conf.template /opt/pastefile/nginx.conf.template
COPY ./extra/Docker/configs/vhost.conf.template /opt/pastefile/vhost.conf.template
COPY ./extra/Docker/scripts/entrypoint /entrypoint

ENTRYPOINT ["/entrypoint"]
