# -*- coding: utf-8 -*-
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

'''Unit testing for this module.
'''

from django.test import TestCase
from django.db import models
from django.core.management.commands.dumpdata import Command as Dumpdata
from fields import PickledObjectField, ListField

class TestingModel(models.Model):
    pickle_field = PickledObjectField()

class List(models.Model):
    items = ListField()

class TestCustomDataType(str):
    pass

class PickledObjectFieldTests(TestCase):
    def setUp(self):
        self.testing_data = (
            {1:1, 2:4, 3:6, 4:8, 5:10},
            'Hello World',
            (1, 2, 3, 4, 5),
            [1, 2, 3, 4, 5],
            TestCustomDataType('Hello World'),
        )
        return super(PickledObjectFieldTests, self).setUp()
    
    def testDataIntegriry(self):
        """Tests that data remains the same when saved to and fetched from
        the database.
        """
        for value in self.testing_data:
            model_test = TestingModel(pickle_field=value)
            model_test.save()
            model_test = TestingModel.objects.get(id__exact=model_test.id)
            self.assertEquals(value, model_test.pickle_field)
            model_test.delete()
    
    def testLookups(self):
        """Tests that lookups can be performed on data once stored
        in the database.
        """
        for value in self.testing_data:
            model_test = TestingModel(pickle_field=value)
            model_test.save()
            self.assertEquals(value, TestingModel.objects.get(pickle_field__exact=value).pickle_field)
            model_test.delete()

    def testFixture(self):
        """Tests that values can be serialized to a fixture.

        XXX BROKEN, see django http://code.djangoproject.com/ticket/9522

        """
        for value in self.testing_data:
            model_test = TestingModel(pickle_field=value)
            model_test.save()
        dumpdata = Dumpdata()
        json = dumpdata.handle('mbdb')
        pass

class PickleFixtureLoad(TestCase):
    fixtures = ['pickle_sample.json']

    def testUnpickle(self):
        self.failUnlessEqual(TestingModel.objects.count(), 3)
        v = TestingModel.objects.get(pk=1).pickle_field
        self.assertEquals(v, u"one string")
        self.assert_(isinstance(v, unicode))
        v = TestingModel.objects.get(pk=2).pickle_field
        self.assert_(isinstance(v, unicode))
        self.assertEquals(v, u"one pickled string")
        v = TestingModel.objects.get(pk=3).pickle_field
        self.assertEquals(v, ['pickled', 'array'])

class ListFixtureLoad(TestCase):
    fixtures = ['list_field_sample.json']

    def testUnpickle(self):
        self.failUnlessEqual(List.objects.count(), 3)
        v = List.objects.get(pk=1).items
        self.assertEquals(v, [u"one string"])
        v = List.objects.get(pk=2).items
        self.assertEquals(v, [u'Array',u'of',u'strings'])
        v = List.objects.get(pk=3).items
        self.assertEquals(v, [u'Joined', u'list', u'of', u'strings'])
