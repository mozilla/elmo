from signoff.models import Milestone, Signoff, Event, Application, AppVersion
from django.contrib import admin

admin.site.register(Application)
admin.site.register(AppVersion)
admin.site.register(Milestone)
admin.site.register(Signoff)
admin.site.register(Event)
