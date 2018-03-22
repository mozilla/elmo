# Not using -slim, as Axel can't figure out where to get packages there.
FROM python:2.7.14-stretch

WORKDIR /app/
RUN groupadd --gid 10001 app && useradd -g app --uid 10001 --shell /usr/sbin/nologin app

# Install OS-level things
COPY ./docker/set_up.sh /tmp/
RUN DEBIAN_FRONTEND=noninteractive /tmp/set_up.sh
RUN pip install uwsgi==2.0.17

# create virtualenv for elmo
RUN pip install -U virtualenv
RUN virtualenv env
COPY ./requirements env/requirements
RUN ./env/bin/pip install -r env/requirements/dev.txt
USER app
COPY --chown=app:app ./ ./elmo/
WORKDIR /app/elmo

CMD ["/app/elmo/docker/run_webapp.sh"]
