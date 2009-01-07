# -*- coding: utf-8 -*-
"""Unit testing for this module."""

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
