# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

'''URL mappings for the bugsy application.
'''

from django.conf.urls.defaults import *

urlpatterns = patterns('bugsy.views',
    (r'^$', 'index'),
    (r'^new-locale$', 'new_locale'),
    (r'^new-locale-bugs.json$', 'new_locale_bugs'),
    (r'^file-bugs$', 'file_bugs'),
    (r'^bug-links$', 'get_bug_links'),
)
