# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

'''URL mappings for l10nstats application.
'''

from django.conf.urls import patterns

urlpatterns = patterns('l10nstats.views',
    (r'^$', 'index'),
    (r'^history$', 'history_plot'),
    (r'^compare$', 'compare', {}, 'compare_locales'),
    (r'^tree-status/([^/]+)$', 'tree_progress'),
)
