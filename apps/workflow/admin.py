# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from django.contrib import admin
from workflow.models import (
  Actor, 
  ProtoProcess, Nesting, ProtoTask, ProtoStep,
  Process, Task, Step)

class NestingInline(admin.TabularInline):
    model = Nesting
    fk_name = 'parent'
    verbose_name_plural = 'Children'
    extra = 0

class ProtoStepInline(admin.TabularInline):
    model = ProtoStep
    verbose_name_plural = 'Steps'
    extra = 0


class ProtoProcessAdmin(admin.ModelAdmin):
    list_display_links = ('summary',)
    list_display = ('id',) + list_display_links
    inlines = [NestingInline]

class ProtoTaskAdmin(admin.ModelAdmin):
    list_display_links = ('summary',)
    list_display = ('id',) + list_display_links
    inlines = [ProtoStepInline]

class ProtoStepAdmin(admin.ModelAdmin):
    list_display_links = ('summary',)
    list_display = ('id',) + list_display_links
    inlines = [ProtoStepInline]


admin.site.register(Actor)
admin.site.register(ProtoProcess, ProtoProcessAdmin)
admin.site.register(ProtoTask, ProtoTaskAdmin)
admin.site.register(ProtoStep, ProtoStepAdmin)
admin.site.register(Process)
admin.site.register(Task)
admin.site.register(Step)
