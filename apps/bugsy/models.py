# ***** BEGIN LICENSE BLOCK *****
# Version: MPL 1.1/GPL 2.0/LGPL 2.1
#
# The contents of this file are subject to the Mozilla Public License Version
# 1.1 (the "License"); you may not use this file except in compliance with
# the License. You may obtain a copy of the License at
# http://www.mozilla.org/MPL/
#
# Software distributed under the License is distributed on an "AS IS" basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied. See the License
# for the specific language governing rights and limitations under the
# License.
#
# The Original Code is l10n django site.
#
# The Initial Developer of the Original Code is
# Mozilla Foundation.
# Portions created by the Initial Developer are Copyright (C) 2010
# the Initial Developer. All Rights Reserved.
#
# Contributor(s):
#
# Alternatively, the contents of this file may be used under the terms of
# either the GNU General Public License Version 2 or later (the "GPL"), or
# the GNU Lesser General Public License Version 2.1 or later (the "LGPL"),
# in which case the provisions of the GPL or the LGPL are applicable instead
# of those above. If you wish to allow use of your version of this file only
# under the terms of either the GPL or the LGPL, and not to allow others to
# use your version of this file under the terms of the MPL, indicate your
# decision by deleting the provisions above and replace them with the notice
# and other provisions required by the GPL or the LGPL. If you do not delete
# the provisions above, a recipient may use your version of this file under
# the terms of any one of the MPL, the GPL or the LGPL.
#
# ***** END LICENSE BLOCK *****

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
