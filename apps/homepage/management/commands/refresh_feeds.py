# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""This managment commands runs all the functions again that pull feeds (parses
them and stores its results in a cache).

Ideally this management command should run in sync with the update job on
planet, but at least every hour.
"""

import time
import logging
from django.conf import settings
from django.core.management.base import BaseCommand
from homepage.views import get_feed_items


class Command(BaseCommand):  # pragma: no cover

    def handle(self, **options):
        verbose = int(options['verbosity']) > 1
        t0 = time.time()
        get_feed_items(force_refresh=True)
        t1 = time.time()
        note = 'Took %.4f to parse %s' % (t1 - t0, settings.L10N_FEED_URL)
        logging.info(note)
        if verbose:
            print get_feed_items
            print "\t", note
