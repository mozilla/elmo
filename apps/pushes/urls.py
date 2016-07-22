# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
from __future__ import absolute_import

from django.conf.urls import url
from . import views

urlpatterns = [
    url(r'^pushes/(?P<repo_name>.+)?$', views.pushlog, name='pushlog'),
    url(r'^diff/$', views.diff, name='diff'),
]
