from django.db import models

from pushes.models import Push

class Milestone(models.Model):
    name = models.CharField(max_length = 50)
    string_freeze = models.DateTimeField()
    l10n_freeze = models.DateTimeField()
    def __unicode__(self):
        return self.name

class Signoff(models.Model):
    revision = models.ForeignKey(Push)
    milestone = models.ForeignKey(Milestone, related_name = 'signoffs')
    # todo, refer to user here. Figure out what ldap auth would give us
    # who = models.CharField(max_length = 100, blank = True, null = True)
