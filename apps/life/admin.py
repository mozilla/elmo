# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from models import Tree, Repository, Locale, Forest
from django.contrib import admin


class RepositoryAdmin(admin.ModelAdmin):
    exclude = ('changesets',)

admin.site.register(Locale)
admin.site.register(Repository, RepositoryAdmin)
admin.site.register(Tree)
admin.site.register(Forest)
