# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
from __future__ import absolute_import

from shipping.models import Action, Application, AppVersion
from django.contrib import admin


admin.site.register(Application)
admin.site.register(AppVersion)
admin.site.register(AppVersion.trees.through)
admin.site.register(Action)
