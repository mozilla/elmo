# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
from __future__ import absolute_import
from __future__ import unicode_literals

from django.contrib.admin import AdminSite
from session_csrf import anonymous_csrf


class CSRFAdminSite(AdminSite):
    def get_urls(self):
        urlpatterns = super(CSRFAdminSite, self).get_urls()
        for pattern in urlpatterns:
            if hasattr(pattern, 'name') and pattern.name == 'login':
                pattern.callback = anonymous_csrf(pattern.callback)
        return urlpatterns


admin_site = CSRFAdminSite()
