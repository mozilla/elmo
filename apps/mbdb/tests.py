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
import datetime
from django.test import TestCase
from django.core.management.commands.dumpdata import Command
from apps.mbdb.models import Property, Step, Build, Builder, Master, Slave
import json


class TestCustomDataType(str):
    pass


class ModelsTest(TestCase):

    def setUp(self):
        self.testing_data = (
            {1: 1, 2: 4, 3: 6, 4: 8, 5: 10},
            'Hello World',
            (1, 2, 3, 4, 5),
            [1, 2, 3, 4, 5],
            TestCustomDataType('Hello World'),
        )
        return super(ModelsTest, self).setUp()

    def testPropertyModel(self):
        """test saving a Property instance with a big fat tuple of various
        types of python data"""
        # proves that 'value' can be null
        prop = Property.objects.create(name='peter', source='foo_bar')
        prop.save()
        self.assertEqual(prop.value, None)
        self.assertEqual(Property.objects.filter(value__isnull=True).count(), 1)

        prop.value = self.testing_data
        prop.save()

        self.assertEqual(Property.objects.filter(value__isnull=True).count(), 0)

        prop = Property.objects.get(name='peter')
        self.assertEqual(prop.value, self.testing_data)

    def testPropertyModelDifferentPickledata(self):
        """test setting the value to be various types of data"""
        for value in self.testing_data:
            # save and...
            prop = Property.objects.create(name='peter', source='foo',
                                           value=value)
            # get back out to ensure it doesn't cache the python object only
            prop = Property.objects.get(value__exact=value)
            self.assertEquals(value, prop.value)
            prop.delete()

    def testPropertyDataDump(self):
        for i, value in enumerate(self.testing_data):
            prop = Property.objects.create(name='name %s' % i,
                                           source='foo',
                                           value=value)
            dumpdata = Command()
            jsondata = dumpdata.handle('mbdb')
            data = json.loads(jsondata)
            value_data = data[0]['fields']['value']
            # dump data will always dump the pickled data stringified
            self.assertEqual(unicode(value), value_data)
            prop.delete()

    def testStepModel(self):
        # pre-requisites
        master = Master.objects.create(
         name='head',
        )

        builder = Builder.objects.create(
          name='builder1',
          master=master,
        )

        slave = Slave.objects.create(
          name='slave 1',
        )

        build = Build.objects.create(
          buildnumber=1,
          builder=builder,
          slave=slave,
          starttime=datetime.datetime.now(),
          endtime=datetime.datetime.now(),
          result=1,
        )

        step = Step.objects.create(
          name='step 1',
          build=build
        )
        # this proves that custom fields `text` and `text2` are optional
        test_list = ['Peter', u'\xa3pounds']
        self.assertEqual(step.text, None)
        self.assertEqual(step.text2, None)
        step.text = test_list
        step.text2 = []
        step.save()

        self.assertTrue(Step.objects.get(text__isnull=False))
        self.assertTrue(Step.objects.get(text=test_list))
        self.assertEqual(Step.objects.filter(text=test_list).count(), 1)
        self.assertEqual(Step.objects.filter(text__isnull=False).count(), 1)
        self.assertEqual(Step.objects.filter(text__isnull=True).count(), 0)

        step = Step.objects.get(name='step 1')
        self.assertEqual(step.text, test_list)
        self.assertEqual(step.text2, [])

        # it must also be possible to go back to null (see model definition)
        step.text = None
        step.save()

        self.assertEqual(Step.objects.filter(text__isnull=False).count(), 0)
        self.assertEqual(Step.objects.filter(text__isnull=True).count(), 1)

        step = Step.objects.get(name='step 1')
        self.assertEqual(step.text, None)
        self.assertEqual(Step.objects.filter(text=test_list).count(), 0)


class ModelsWithPickleFixtureTest(TestCase):
    fixtures = ['pickle_sample.json']

    def testPropertyModel(self):
        prop = Property.objects.get(name='one')
        self.assertEqual(prop.value, u'one string')
        prop = Property.objects.get(name='two')
        self.assertEqual(prop.value, u'one pickled string')
        prop = Property.objects.get(name='three')
        self.assertEqual(prop.value, ['pickled', 'array'])


class ModelsWithListFixtureTest(TestCase):
    fixtures = ['list_field_sample.json']

    def testStepModel(self):
        step = Step.objects.get(name='step 1')
        self.assertEqual(step.text, [u'Peter', u'Be'])
        self.assertEqual(step.text2, [])

        step = Step.objects.get(name='step 2')
        self.assertEqual(step.text, [u'Joined', u'list', u'of', u'strings'])
        self.assertEqual(step.text2, None)
