# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

'''URL mappings for l10nstats application.
'''
from __future__ import absolute_import

from django.conf.urls import url
from . import views

urlpatterns = [
    url(r'^$', views.index),
    url(r'^history$', views.history_plot, name='locale-tree-history'),
    url(r'^compare$', views.CompareView.as_view(), name='compare-locales'),
    url(r'^tree-status/([^/]+)$', views.tree_progress, name='tree-history'),
]
