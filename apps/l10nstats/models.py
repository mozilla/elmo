# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

'''Models for compare-locales statistics.
'''
from __future__ import absolute_import

from django.db import models
from life.models import Locale, Tree, Changeset
from mbdb.models import Build


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
    locale = models.ForeignKey(Locale, db_index=True, on_delete=models.CASCADE)
    tree = models.ForeignKey(Tree, db_index=True, on_delete=models.CASCADE)
    build = models.OneToOneField(Build, null=True, blank=True,
                                 on_delete=models.SET_NULL)
    srctime = models.DateTimeField(db_index=True, null=True, blank=True)
    revisions = models.ManyToManyField(Changeset)
    missing = models.IntegerField(default=0)
    missingInFiles = models.IntegerField(default=0)
    obsolete = models.IntegerField(default=0)
    total = models.IntegerField(default=0)
    changed = models.IntegerField(default=0)
    unchanged = models.IntegerField(default=0)
    keys = models.IntegerField(default=0)
    errors = models.IntegerField(default=0)
    report = models.IntegerField(default=0)
    warnings = models.IntegerField(default=0)
    completion = models.SmallIntegerField(default=0)

    @property
    def allmissing(self):
        """property adding missing and missingInFiles to be used in templates
        etc.

        We keep track of missing strings in existing files and in new files
        separetely, add the two for the most stats here.
        """
        return self.missing + self.missingInFiles

    def activate(self):
        previous = Active.objects.filter(run__tree=self.tree,
                                         run__locale=self.locale)
        previousl = list(previous)
        if len(previousl) == 1:
            previousl[0].run = self
            previousl[0].save()
        else:
            if previousl:
                previous.delete()
            Active.objects.create(run=self)

    # fields and class method to convert a query over runs to a brief text
    dfields = ['errors', 'missing', 'missingInFiles',
               'obsolete',
               'completion']

    @classmethod
    def to_class_string(cls, iterable, prefix=''):
        """Convert an iterable list of dictionaries to brief output, and
        result.

        The input can be a values() query ending up on Run objects, and needs
        all the fields in dfields. The given prefix can be used if the
        Runs are not the primary manager.

        Yields triples of the input dictionary, the short text, and a
        classification, any of "error", "warnings", or "success".
        """
        for d in iterable:
            cmp_segs = []
            cls = None
            if d[prefix + 'errors']:
                cmp_segs.append('%d error(s)' % d[prefix + 'errors'])
                cls = 'failure'
            missing = d[prefix + 'missing'] + d[prefix + 'missingInFiles']
            if missing:
                cmp_segs.append('%d missing' % missing)
                cls = 'failure'
            if d[prefix + 'obsolete']:
                cmp_segs.append('%d obsolete' % d[prefix + 'obsolete'])
                cls = cls is None and 'warnings' or cls
            if cmp_segs:
                compare = ', '.join(cmp_segs)
            else:
                compare = 'green (%d%%)' % d[prefix + 'completion']
                cls = 'success'
            yield (d, cls, compare)



class Active(models.Model):
    """Keep track of the currently active Runs.
    """
    run = models.OneToOneField(Run, on_delete=models.CASCADE)


class ProgressPosition(models.Model):
    """Position in the background image
    """
    tree = models.ForeignKey(Tree, on_delete=models.CASCADE)
    locale = models.ForeignKey(Locale, on_delete=models.CASCADE)
    x = models.IntegerField()
    y = models.IntegerField()
