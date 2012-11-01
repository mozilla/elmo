# -*- coding: utf-8 -*-
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

'''Unit testing for this module.
'''
import datetime
from test_utils import TestCase
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
        self.assertEqual(Property.objects.filter(value__isnull=True).count(),
                         1)

        prop.value = self.testing_data
        prop.save()

        self.assertEqual(Property.objects.filter(value__isnull=True).count(),
                         0)

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
            # when calling handle() directly it's unable to pick up defaults
            # in Command.option_list so we have to pick that up manually
            defaults = dict(
                (x.dest, x.default) for x in Command.option_list
            )
            jsondata = dumpdata.handle('mbdb', **defaults)
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
          starttime=datetime.datetime.utcnow(),
          endtime=datetime.datetime.utcnow(),
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
