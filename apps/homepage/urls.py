# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

'''URL mappings for the l10n_site integration pages.
'''
from __future__ import absolute_import

from django.conf.urls import url
from . import views

urlpatterns = [
    url(r'^$', views.index, name='homepage'),
    url(r'^teams/$', views.teams, name='teams'),
    url(r'^teams/(.*)$', views.locale_team, name='l10n-team'),
    url(r'^pushes/(.*)$', views.pushlog_redirect),
    url(r'^shipping/diff$', views.diff_redirect),
]
