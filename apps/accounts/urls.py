# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

'Url mappings for accounts app'
from __future__ import absolute_import
from __future__ import unicode_literals

from django.conf.urls import url
from . import views

urlpatterns = [
    url(r'^login', views.login, name='login'),
    url(r'^user.json$', views.user_json, name='user-json'),
    url(r'^logout$', views.logout, name='logout'),
]
