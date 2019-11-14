ARG pythonversion
FROM python:${pythonversion}-slim-stretch

WORKDIR /app/
RUN groupadd --gid 10001 app && useradd -g app --uid 10001 --shell /usr/sbin/nologin app

# Install OS-level things
COPY ./docker/set_up.sh /tmp/
RUN DEBIAN_FRONTEND=noninteractive /tmp/set_up.sh
RUN pip install uwsgi==2.0.18

# create virtualenv for elmo
RUN pip install -U virtualenv
RUN virtualenv env
COPY ./requirements env/requirements
RUN ./env/bin/pip install -r env/requirements/dev.txt
RUN mkdir /app/collected
RUN chown app:app /app/collected
USER app
COPY --chown=app:app . /app/
RUN ELMO_SECRET_KEY=foo /app/env/bin/python manage.py collectstatic --no-input
RUN ELMO_SECRET_KEY=foo /app/env/bin/python manage.py compress --force

CMD ["/app/docker/run_webapp.sh"]
