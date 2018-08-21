# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

'Base command to include ES logging'
from __future__ import absolute_import
from __future__ import unicode_literals

import logging
from django.core.management.base import BaseCommand


class LoggingCommand(BaseCommand):

    class Logger(logging.Handler):

        def __init__(self, cmd):
            logging.Handler.__init__(self)
            self.cmd = cmd

        def emit(self, record):
            pass

    def handle(self, **options):
        handler = self.Logger(self)
        logging.getLogger('elasticsearch').addHandler(handler)
        self.handleWithLogging(**options)
