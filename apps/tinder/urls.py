# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

'''URL mappings for the tinder app.
'''

from django.conf.urls import patterns, url
from views import BuildsForChangeFeed


urlpatterns = patterns('tinder.views',
                       (r'^waterfall$', 'waterfall'),
                       (r'^tbpl$', 'tbpl'),
                       (r'^tbpl-rows$', 'tbpl_rows', {}, 'tinder_update_tbpl'),
                       (r'^builds_for', 'builds_for_change'),
                       (r'^builders/([^/]+)/(\d+)', 'showbuild',
                        {}, 'tinder_show_build'),
                       (r'^log/([0-9]+)/([^/]+)$', 'showlog', {}, 'showlog'),
                       # feed instances need a name so use url() here
                       url(r'^feeds/builds_for_change/(\d+)/$',
                           BuildsForChangeFeed(), name='BuildsForChangeFeed'),
                       )
