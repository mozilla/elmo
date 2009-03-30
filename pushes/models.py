from django.db import models

from django.conf import settings

"""Model module for pushes.

These models map the remote pushlog db from hg.mozilla.org onto 
a local database.
"""

class Forest(models.Model):
    name = models.CharField(max_length=100)
    url = models.URLField()
    def __unicode__(self):
        return self.name

class Repository(models.Model):
    name = models.CharField(max_length=100)
    url = models.URLField()
    last_known_push = models.PositiveIntegerField(default=0)
    forest = models.ForeignKey(Forest, null=True, blank=True)
    def __unicode__(self):
        return self.name

class Push(models.Model):
    repository = models.ForeignKey(Repository)
    user = models.CharField(max_length=200, db_index=True)
    push_date = models.DateTimeField('date of push', db_index=True)
    push_id = models.PositiveIntegerField(default=0)

if 'mbdb' in settings.INSTALLED_APPS:
    from mbdb.models import File
else:
    class File(models.Model):
        class Meta:
            db_table = 'mbdb_file'
        path = models.CharField(max_length=400, db_index=True)
        def __unicode__(self):
            return self.path

class Changeset(models.Model):
    push = models.ForeignKey(Push, related_name='changesets')
    revision = models.CharField(max_length=40, db_index=True)
    user = models.CharField(null = True, blank = True, max_length=100, db_index=True)
    description = models.TextField(null = True, blank = True, db_index=True)
    files = models.ManyToManyField(File)
