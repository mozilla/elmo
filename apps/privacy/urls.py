# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

'''URL mappings for the privacy app.
'''

from django.conf.urls.defaults import patterns

urlpatterns = patterns('privacy.views',
                       (r'^(?P<id>\d+)?$', 'show_policy'),
                       (r'^versions$', 'versions'),
                       (r'^add$', 'add_policy'),
                       (r'^activate$', 'activate_policy'),
                       (r'^comment$', 'add_comment'),
                       )
