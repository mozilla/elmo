# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

'''Consume data from pulse and insert it into the database.
'''
from __future__ import absolute_import
from __future__ import unicode_literals

import logging

from django.conf import settings
from django.core.management.base import BaseCommand

from kombu import Connection

from elmo_queues.consumers import ElmoConsumer


class Command(BaseCommand):
    help = 'Consume data from pulse.m.o'

    def add_arguments(self, parser):
        pass

    def handle(self, *args, **options):
        logging.basicConfig(
            level=logging.INFO, format="%(asctime)s - %(message)s"
        )
        with Connection(
            hostname=settings.PULSE_HOST,
            userid=settings.PULSE_USER,
            password=settings.PULSE_PASSWORD,
            ssl=settings.PULSE_SSL
        ) as pulse:
            pulse.connect()
            c = ElmoConsumer(pulse)
            try:
                # import pdb; pdb.set_trace()
                c.run()
            except KeyboardInterrupt:
                pass
            finally:
                pulse.release()
