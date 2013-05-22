# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from django.conf.urls import patterns

urlpatterns = patterns('pushes.views',
                       (r'^pushes/(?P<repo_name>.+)?$', 'pushlog'),
                       (r'^diff/$', 'diff'),
                       # external APIs below, web apps can use these
                       (r'^api/network/$', 'api.network'),
                       (r'^api/forks/(.+)/?$', 'api.forks'),
)
