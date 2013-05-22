# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

'''URL mappings for the l10n_site integration pages.
'''

from django.conf.urls import patterns

urlpatterns = patterns('homepage.views',
                       (r'^$', 'index'),
                       (r'^teams/$', 'teams'),
                       (r'^teams/(.*)$', 'locale_team'),
                       (r'^pushes/(.*)$', 'pushlog_redirect'),
                       (r'^shipping/diff$', 'diff_redirect'),
                       )
