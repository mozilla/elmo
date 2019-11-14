#!/bin/bash

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# Runs the webapp.
#
# Use the "--dev" argument to run the webapp in a docker container for
# the purposes of local development.

set -e

BUFFER_SIZE=${BUFFER_SIZE:-"16384"}
PORT=${PORT:-"8000"}
NUM_WORKERS=${NUM_WORKERS:-"6"}
UWSGI_OPT_MEMORY=${UWSGI_OPT_MEMORY:-"200"}
UWSGI_HARAKIRI=${UWSGI_HARAKIRI:-"60"}

if [ "$1" == "--dev" ]; then
    # Run with manage.py
    echo "******************************************************************"
    echo "Running webapp in local dev environment."
    echo "Connect with your browser using: http://localhost:8000/ "
    echo "******************************************************************"
    cd /app/ && ${CMDPREFIX} python manage.py runserver 0.0.0.0:8000

else
    # Run uwsgi
    ${CMDPREFIX} uwsgi \
                 --pythonpath /app/:/app/apps/ \
                 --master \
                 --need-app \
                 --wsgi-file  /app/wsgi/elmo.wsgi \
                 --buffer-size "${BUFFER_SIZE}" \
                 --reload-on-rss "${UWSGI_OPT_MEMORY}" \
                 --harakiri "${UWSGI_HARAKIRI}" \
                 --enable-threads \
                 --processes "${NUM_WORKERS}" \
                 --http-socket 0.0.0.0:"${PORT}"
fi
