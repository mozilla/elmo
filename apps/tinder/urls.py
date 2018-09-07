# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

'''URL mappings for the tinder app.
'''
from __future__ import absolute_import
from __future__ import unicode_literals

from django.conf.urls import url
from . import views


urlpatterns = [
    url(r'^waterfall$', views.waterfall),
    url(r'^tbpl$', views.tbpl),
    url(r'^tbpl-rows$', views.tbpl_rows, name='tinder-update-tbpl'),
    url(r'^builds_for', views.builds_for_change),
    url(r'^builders/([^/]+)/(\d+)', views.showbuild, name='tinder-showbuild'),
    url(r'^log/([0-9]+)/([^/]+)$', views.showlog, name='tinder-showlog'),
    # feed instances need a name so use url() here
    url(r'^feeds/builds_for_change/(\d+)/$',
        views.BuildsForChangeFeed(), name='BuildsForChangeFeed'),
]
