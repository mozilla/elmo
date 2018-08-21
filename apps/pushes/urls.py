# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
from __future__ import absolute_import
from __future__ import unicode_literals

from django.conf.urls import url
from .views import diff, pushlog

app_name = 'pushes'
urlpatterns = [
    url(r'^pushes/(?P<repo_name>.+)?$', pushlog.pushlog, name='pushlog'),
    url(r'^diff/$', diff.DiffView.as_view(), name='diff'),
]
