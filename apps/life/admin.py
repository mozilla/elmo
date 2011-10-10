from models import Tree, Repository, Locale, Forest
from django.contrib import admin


class RepositoryAdmin(admin.ModelAdmin):
    exclude = ('changesets',)

admin.site.register(Locale)
admin.site.register(Repository, RepositoryAdmin)
admin.site.register(Tree)
admin.site.register(Forest)
