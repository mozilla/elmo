from django.db import models

from django.conf import settings

"""Model module for pushes.

These models map the remote pushlog db from hg.mozilla.org onto 
a local database.
"""

class Repository(models.Model):
    name = models.CharField(max_length=100)
    url = models.URLField()
    last_known_push = models.PositiveIntegerField(default=0)
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
    push = models.ForeignKey(Push)
    revision = models.CharField(max_length=40)
    files = models.ManyToManyField(File)
