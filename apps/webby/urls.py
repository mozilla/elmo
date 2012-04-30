# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from django.conf.urls.defaults import patterns, url
from webby.feeds import AllOptinsFeed, PendingOptinsFeed

urlpatterns = patterns('webby.views',
    (r'^$', 'projects'),
    url(r'^(?P<slug>[\w-]+)$', 'project', name="webby-project"),
    (r'^feed/all$', AllOptinsFeed()),
    (r'^feed/pending$', PendingOptinsFeed()),
)
