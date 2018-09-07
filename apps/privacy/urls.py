# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

'''URL mappings for the privacy app.
'''
from __future__ import absolute_import
from __future__ import unicode_literals

from django.conf.urls import url
from . import views

app_name = 'privacy'
urlpatterns = [
    url(r'^(?P<id>\d+)?$', views.show_policy, name='show'),
    url(r'^versions$', views.versions, name='versions'),
    url(r'^add$', views.add_policy, name='add'),
    url(r'^activate$', views.activate_policy, name='activate'),
    url(r'^comment$', views.add_comment, name='comment'),
]
