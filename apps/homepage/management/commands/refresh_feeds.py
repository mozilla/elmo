# ***** BEGIN LICENSE BLOCK *****
# Version: MPL 1.1/GPL 2.0/LGPL 2.1
#
# The contents of this file are subject to the Mozilla Public License Version
# 1.1 (the "License"); you may not use this file except in compliance with
# the License. You may obtain a copy of the License at
# http://www.mozilla.org/MPL/
#
# Software distributed under the License is distributed on an "AS IS" basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied. See the License
# for the specific language governing rights and limitations under the
# License.
#
# The Original Code is l10n django site.
#
# The Initial Developer of the Original Code is
# Mozilla Foundation.
# Portions created by the Initial Developer are Copyright (C) 2010
# the Initial Developer. All Rights Reserved.
#
# Contributor(s):
#
# Alternatively, the contents of this file may be used under the terms of
# either the GNU General Public License Version 2 or later (the "GPL"), or
# the GNU Lesser General Public License Version 2.1 or later (the "LGPL"),
# in which case the provisions of the GPL or the LGPL are applicable instead
# of those above. If you wish to allow use of your version of this file only
# under the terms of either the GPL or the LGPL, and not to allow others to
# use your version of this file under the terms of the MPL, indicate your
# decision by deleting the provisions above and replace them with the notice
# and other provisions required by the GPL or the LGPL. If you do not delete
# the provisions above, a recipient may use your version of this file under
# the terms of any one of the MPL, the GPL or the LGPL.
#
# ***** END LICENSE BLOCK *****
"""This managment commands runs all the functions again that pull feeds (parses
them and stores its results in a cache).

Ideally this management command should be run every hour. That prevents the
home page view from having to block on network problems.
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
