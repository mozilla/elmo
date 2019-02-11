# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
from __future__ import absolute_import
from __future__ import unicode_literals

from .models import Tree, Repository, Locale, Forest
from django.contrib import admin


class RepositoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'id',)
    exclude = ('changesets',)
    search_fields = ('name',)


admin.site.register(Locale)
admin.site.register(Repository, RepositoryAdmin)
admin.site.register(Tree)
admin.site.register(Forest)
