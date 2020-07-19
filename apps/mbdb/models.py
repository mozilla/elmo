# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

'''Models representing statuses of buildbot builds on multiple mains.
'''
from __future__ import absolute_import
from __future__ import unicode_literals

from django.db import models
from django.utils.encoding import python_2_unicode_compatible
from . import fields
from django.conf import settings
import six


@python_2_unicode_compatible
class Main(models.Model):
    """Model for a buildbot main"""
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


@python_2_unicode_compatible
class Subordinate(models.Model):
    """Model for a build subordinate"""
    name = models.CharField(max_length=150, unique=True)

    def __str__(self):
        return self.name


@python_2_unicode_compatible
class File(models.Model):
    """Model for files throughout"""
    # not  unique = True, mysql doesn't like long unique utf-8 strings
    path = models.CharField(max_length=400)

    def __str__(self):
        return self.path


@python_2_unicode_compatible
class Tag(models.Model):
    """Model to add tags to the Change model"""
    value = models.CharField(max_length=50, db_index=True, unique=True)

    def __str__(self):
        return self.value


@python_2_unicode_compatible
class Change(models.Model):
    """Model for buildbot.changes.changes.Change"""
    number = models.PositiveIntegerField()
    main = models.ForeignKey(Main, on_delete=models.CASCADE)
    branch = models.CharField(max_length=100, null=True, blank=True)
    revision = models.CharField(max_length=50, null=True, blank=True)
    who = models.CharField(max_length=100, null=True, blank=True,
                           db_index=True)
    files = models.ManyToManyField(File)
    comments = models.TextField(null=True, blank=True)
    when = models.DateTimeField()
    tags = models.ManyToManyField(Tag)

    class Meta:
        unique_together = (('number', 'main'),)

    def __str__(self):
        rv = 'Change %d' % self.number
        if self.branch:
            rv += ', ' + self.branch
        if self.tags:
            rv += ' (%s)' % ', '.join(
                (six.text_type(t) for t in self.tags.all())
            )
        return rv


class SourceStamp(models.Model):
    changes = models.ManyToManyField(Change, through='NumberedChange',
                                     related_name='stamps')
    branch = models.CharField(max_length=100, null=True, blank=True)
    revision = models.CharField(max_length=50, null=True, blank=True)


class NumberedChange(models.Model):
    change = models.ForeignKey(Change, related_name='numbered_changes',
                               on_delete=models.CASCADE)
    sourcestamp = models.ForeignKey(SourceStamp,
                                    related_name='numbered_changes',
                                    on_delete=models.CASCADE)
    number = models.IntegerField(db_index=True)


# this is needed inside the Meta class of the Property class but because we're
# not allowed to creat variables inside the class itself, we figure out what
# database engine we're using *before* defining the Property class.
try:
    database_engine = settings.DATABASES['default']['ENGINE']
except KeyError:
    database_engine = settings.DATABASE_ENGINE


@python_2_unicode_compatible
class Property(models.Model):
    """Helper model for build properties.

    To support complex property values, they are internally pickled.
    """
    name = models.CharField(max_length=40, db_index=True)
    source = models.CharField(max_length=20, db_index=True)
    value = fields.PickledObjectField(null=True, blank=True)

    class Meta:
        if not database_engine.endswith('mysql'):
            # hack around mysql, that doesn't do unique of unconstrained texts
            unique_together = (('name', 'source', 'value'),)

    def __str__(self):
        return "%s: %s" % (self.name, self.value)


@python_2_unicode_compatible
class Builder(models.Model):
    """Model for buildbot.status.builder.BuilderStatus"""
    name = models.CharField(max_length=50, unique=True, db_index=True)
    main = models.ForeignKey(Main, related_name='builders',
                               on_delete=models.CASCADE)
    category = models.CharField(max_length=30, null=True, blank=True,
                                db_index=True)
    bigState = models.CharField(max_length=30, null=True, blank=True)

    def __str__(self):
        return 'Builder <%s>' % self.name


@python_2_unicode_compatible
class Build(models.Model):
    """Model for buildbot..status.builder.Build
    """
    buildnumber = models.IntegerField(null=True, db_index=True)
    properties = models.ManyToManyField(Property, related_name='builds')
    builder = models.ForeignKey(Builder, related_name='builds',
                                on_delete=models.CASCADE)
    subordinate = models.ForeignKey(Subordinate, null=True, blank=True,
                              on_delete=models.SET_NULL)
    starttime = models.DateTimeField(null=True, blank=True)
    endtime = models.DateTimeField(null=True, blank=True)
    result = models.SmallIntegerField(null=True, blank=True)
    reason = models.CharField(max_length=50, null=True, blank=True)
    sourcestamp = models.ForeignKey(SourceStamp, null=True,
                                    on_delete=models.SET_NULL,
                                    related_name='builds')

    def setProperty(self, name, value, source):
        if name in ('buildername', 'buildnumber'):
            # we have those in the db, ignore
            return
        try:
            # First, see if we have the property, or a property of that name,
            # at least.
            prop = self.properties.get(name=name)
            if prop.value == value and prop.source == source:
                # we already know this, we're done
                return
            if prop.builds.count() < 2:
                # this is our own property, clean up the table
                prop.delete()
            else:
                # otherwise, unbind the property, and fake a DoesNotExist
                self.properties.remove(prop)
        except Property.DoesNotExist:
            pass
        prop, created = Property.objects.get_or_create(name=name,
                                                       source=source,
                                                       value=value)
        self.properties.add(prop)

    def getProperty(self, name, default=None):
        if name == 'buildername':
            # hardcode, we know that
            return self.builder.name
        if name == 'buildnumber':
            # hardcode, we know that
            return self.buildnumber
        # all others are real properties, query the db
        try:
            prop = self.properties.get(name=name)
        except Property.DoesNotExist:
            return default
        return prop.value

    def propertiesAsList(self):
        prop_list = [
            (p.name, p.value, p.source) for p in self.properties.iterator()
        ]
        # hardcode buildername and buildnumber again
        prop_list += [
            ('buildername', self.builder.name, 'Build'),
            ('buildnumber', self.buildnumber, 'Build')
        ]
        prop_list.sort()
        return prop_list

    def __str__(self):
        v = self.builder.name
        if self.buildnumber is not None:
            v += ': %d' % self.buildnumber
        return v


class Step(models.Model):
    name = models.CharField(max_length=50)
    text = fields.ListField(null=True, blank=True)
    text2 = fields.ListField(null=True, blank=True)
    result = models.SmallIntegerField(null=True, blank=True)
    starttime = models.DateTimeField(null=True, blank=True)
    endtime = models.DateTimeField(null=True, blank=True)
    build = models.ForeignKey(Build, related_name='steps',
                              on_delete=models.CASCADE)


class URL(models.Model):
    name = models.CharField(max_length=20)
    url = models.URLField()
    step = models.ForeignKey(Step, related_name='urls',
                             on_delete=models.CASCADE)


@python_2_unicode_compatible
class Log(models.Model):
    STDOUT, STDERR, HEADER = range(3)
    JSON = 5
    CHANNEL_NAMES = ('stdout', 'stderr', 'header', None, None, 'json')
    name = models.CharField(max_length=100, null=True, blank=True)
    filename = models.CharField(max_length=200, unique=True,
                                null=True, blank=True)
    step = models.ForeignKey(Step, related_name='logs',
                             on_delete=models.CASCADE)
    isFinished = models.BooleanField(default=False)
    html = models.TextField(null=True, blank=True)

    def __str__(self):
        if self.filename:
            return self.filename
        return 'HTMLLog %d' % self.id


class BuildRequest(models.Model):
    """Buildrequest status model"""
    builder = models.ForeignKey(Builder, on_delete=models.CASCADE)
    submitTime = models.DateTimeField()
    builds = models.ManyToManyField(Build, related_name='requests')
    sourcestamp = models.ForeignKey(SourceStamp, related_name='requests',
                                    on_delete=models.CASCADE)
