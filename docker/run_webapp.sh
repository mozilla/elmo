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

mkdir -p /app/elmo/collected/static/l10nstats
(cd /app/elmo/ && ${CMDPREFIX} /app/env/bin/python manage.py progress)

if [ 1 ] || [ "$1" == "--dev" ]; then
    # Run with manage.py
    echo "******************************************************************"
    echo "Running webapp in local dev environment."
    echo "Connect with your browser using: http://localhost:8000/ "
    echo "******************************************************************"
    cd /app/elmo/ && ${CMDPREFIX} /app/env/bin/python manage.py runserver 0.0.0.0:8000

else
    # Run uwsgi
    ${CMDPREFIX} uwsgi --pythonpath /app/webapp-django/ \
                 --master \
                 --need-app \
                 --wsgi webapp-django.wsgi.socorro-crashstats \
                 --buffer-size "${BUFFER_SIZE}" \
                 --enable-threads \
                 --processes "${NUM_WORKERS}" \
                 --http-socket 0.0.0.0:"${PORT}"
fi
