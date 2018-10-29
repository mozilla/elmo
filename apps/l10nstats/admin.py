# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
from __future__ import absolute_import
from __future__ import unicode_literals

from .models import Active
from django.contrib import admin


class ActiveAdmin(admin.ModelAdmin):
    exclude = ('run',)
    search_fields = ['run__tree__code', 'run__locale__code', 'run__locale__name']


admin.site.register(Active, ActiveAdmin)
