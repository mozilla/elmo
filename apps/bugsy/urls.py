# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

'''URL mappings for the bugsy application.
'''
from __future__ import absolute_import
from __future__ import unicode_literals

from django.conf.urls import url
from . import views

urlpatterns = [
    url(r'^$', views.index, name='bugsy'),
    url(r'^new-locale$', views.new_locale),
    url(r'^new-locale-bugs.json$', views.new_locale_bugs,
        name='new-locale-bugs'),
    url(r'^file-bugs$', views.file_bugs, name='file-bugs'),
    url(r'^bug-links$', views.get_bug_links, name='get-bug-links'),
]
