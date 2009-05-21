from django.db import models
from life.models import Locale, Tree, Changeset
from mbdb.models import Build

class ModuleCount(models.Model):
    """Abstraction of untranslated strings per module.
    
    Module is usually something like 'browser' or 'security/manager'
    """
    name = models.CharField(max_length=50)
    count = models.IntegerField()
    def __unicode__(self):
        return self.name + '(%d)' % self.count

'''
class Revision(models.Model):
    repository = models.ForeignKey(Repository, related_name='revisions',
                                   db_index=True)
    ident = models.CharField(max_length=40, db_index=True)
    class Meta:
        unique_together = (('repository', 'ident'),)
'''

class Run(models.Model):
    """Abstraction for a inspect-locales run.
    """
    cleanupUnchanged = True

    locale = models.ForeignKey(Locale, db_index=True)
    tree = models.ForeignKey(Tree, db_index=True)
    build = models.OneToOneField(Build, null=True, blank=True)
    srctime = models.DateTimeField(db_index=True, null=True, blank=True)
    unchangedmodules = models.ManyToManyField(ModuleCount, related_name='runs')
    revisions = models.ManyToManyField(Changeset)
    missing = models.IntegerField(default=0)
    missingInFiles = models.IntegerField(default=0)
    obsolete = models.IntegerField(default=0)
    total = models.IntegerField(default=0)
    changed = models.IntegerField(default=0)
    unchanged = models.IntegerField(default=0)
    keys = models.IntegerField(default=0)
    errors = models.IntegerField(default=0)
    completion = models.SmallIntegerField(default=0)

    def activate(self):
        previous = Active.objects.filter(run__tree = self.tree, run__locale = self.locale)
        previousl = list(previous)
        if self.cleanupUnchanged:
            UnchangedInFile.objects.filter(run__in=previous).delete()
        if len(previousl) == 1:
            previousl[0].run = self
            previousl[0].save()
        else:
            if previousl:
                previous.delete()
            Active.objects.create(run=self)


class UnchangedInFile(models.Model):
    """Abstraction for untranslated count per file.
    """
    module = models.CharField(max_length=50, db_index=True)
    file = models.CharField(max_length=400, db_index=True)
    count = models.IntegerField(db_index=True)
    run = models.ForeignKey(Run)

    def __unicode__(self):
        return "%s/%s: %d" % (self.module, self.file, self.count)


class Active(models.Model):
    """Keep track of the currently active Runs.
    """
    run = models.OneToOneField(Run)
