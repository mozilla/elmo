# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from shipping.models import (
  Action, Milestone, Event, Application, AppVersion)
from django.contrib import admin


class MilestoneAdmin(admin.ModelAdmin):
    exclude = ('signoffs',)


admin.site.register(Application)
admin.site.register(AppVersion)
admin.site.register(Milestone, MilestoneAdmin)
admin.site.register(Action)
admin.site.register(Event)
