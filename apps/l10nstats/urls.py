# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

'''URL mappings for l10nstats application.
'''
from __future__ import absolute_import
from __future__ import unicode_literals

from django.conf.urls import url
from . import views
from .views import plots, compare
from .views.progress import ProgressView, ProgressLayout

urlpatterns = [
    url(r'^$', views.index),
    url(r'^history$', plots.history_plot, name='locale-tree-history'),
    url(r'^compare$', compare.CompareView.as_view(), name='compare-locales'),
    url(r'^tree-status/([^/]+)$', plots.tree_progress, name='tree-history'),
    url(r'^progress.css$', ProgressView.as_view(), name='progress-css'),
    url(
        r'^progress-layout.css$',
        ProgressLayout.as_view(),
        name='progress-layout'
    ),
]
