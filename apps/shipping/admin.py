from shipping.models import Action, Milestone, Signoff, Event, Application, AppVersion
from django.contrib import admin

class MilestoneAdmin(admin.ModelAdmin):
    exclude=('signoffs',)

admin.site.register(Application)
admin.site.register(AppVersion)
admin.site.register(Milestone, MilestoneAdmin)
admin.site.register(Action)
admin.site.register(Event)
