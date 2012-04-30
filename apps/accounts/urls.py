# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

'Url mappings for accounts app'

from django.conf.urls.defaults import patterns

urlpatterns = patterns('accounts.views',
    (r'^login', 'login'),
    (r'^user.json$', 'user_json'),
    (r'^logout$', 'logout'),
)
