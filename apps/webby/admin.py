# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from webby.models import Project, ProjectType, Weblocale
from django.contrib import admin


class WeblocaleInline(admin.TabularInline):
    model = Weblocale


class ProjectAdmin(admin.ModelAdmin):
    prepopulated_fields = {"slug": ("name",)}
    inlines = [WeblocaleInline, ]


class WeblocaleAdmin(admin.ModelAdmin):
    list_display = ['__unicode__', 'requestee', 'in_verbatim', 'in_vcs',
                    'is_on_stage', 'is_on_prod']
    list_display_links = ['__unicode__']
    list_editable = ['in_verbatim', 'in_vcs', 'is_on_stage', 'is_on_prod']
    list_filter = ['project']
    search_fields = ['project__name', 'project__slug', 'locale__code',
                     'locale__name']


admin.site.register(ProjectType)
admin.site.register(Project, ProjectAdmin)
admin.site.register(Weblocale, WeblocaleAdmin)
