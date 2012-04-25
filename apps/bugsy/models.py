# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from django.db import models

from life.models import Locale

'''Models to map bugzilla.mozilla.org l10n components and to store
templated bug suites, to be filed on new localizations.
'''

"""
class BugAccount(models.Model):
    '''Simple factorization for the bugzilla ids we have everywhere.'''
    b_id = models.EmailField(unique=True)


class BugComponent(models.Model):
    '''Flat representation of a bugzilla component.

    Doesn't model the categorization, because we don't need that right now.
    '''
    product = models.CharField(max_length=60)
    component = models.CharField(max_length=60)
    owner = models.ForeignKey(BugAccount, null=True, blank=True,
                              related_name='owns')
    qa = models.ForeignKey(BugAccount, null=True, blank=True,
                           related_name='qas')
    cc = models.ManyToManyField(BugAccount, related_name='components')
    locale = models.ForeignKey(Locale, related_name='components')
    class Meta:
        unique_together = (('product', 'component'),)


class BugSuite(models.Model):
    '''Model for a suite of bugs to be filed in one go.

    The actual data is in BugTemplate entries, which reference the suite
    through a ForeignKey.
    '''
    title = models.CharField(max_length=50)


FIELD_CHOICES = (
    ('alias', 'Alias'),
    ('blocks', 'Blocks'),
    ('cc', 'CC'),
    ('component', 'Component'),
    ('depends_on', 'Depends on'),
    ('keywords', 'Keywords'),
    ('op_sys', 'Operating System'),
    ('platform', 'Platform'),
    ('product', 'Product'),
    ('summary', 'Summary'),
    ('whiteboard', 'Status Whiteboard'),
    # somewhat special, need to wrap this as first in a list
    ('comments', 'Description'),
)
class FieldTemplate(models.Model):
    '''A single field and the template to use to fill in the values.
    '''
    field = models.CharField(max_length=20, choices=FIELD_CHOICES)
    template = models.TextField()


class BugTemplate(models.Model):
    '''Mapping between suite and the fields to be given for each bug of that
    suite.
    '''
    title = models.CharField(max_length=50)
    fields = models.ManyToManyField(FieldTemplate, related_name='bug_templates')
    suite = models.ForeignKey(BugSuite, related_name='bugs')
    position = models.IntegerField() # used to order bugs, not necessarily 1,2,3
    depends = models.ManyToManyField("self", symmetrical=False,
                                     related_name="blocks")
"""
