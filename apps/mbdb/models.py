# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

'''Models representing statuses of buildbot builds on multiple masters.
'''

from django.db import models
import fields
from django.conf import settings


class Master(models.Model):
    """Model for a buildbot master"""
    name = models.CharField(max_length=100, unique=True)

    def __unicode__(self):
        return self.name


class Slave(models.Model):
    """Model for a build slave"""
    name = models.CharField(max_length=150, unique=True)

    def __unicode__(self):
        return self.name


class File(models.Model):
    """Model for files throughout"""
    # not  unique = True, mysql doesn't like long unique utf-8 strings
    path = models.CharField(max_length=400)

    def __unicode__(self):
        return self.path


class Tag(models.Model):
    """Model to add tags to the Change model"""
    value = models.CharField(max_length=50, db_index=True, unique=True)

    def __unicode__(self):
        return self.value


class Change(models.Model):
    """Model for buildbot.changes.changes.Change"""
    number = models.PositiveIntegerField()
    master = models.ForeignKey(Master)
    branch = models.CharField(max_length=100, null=True, blank=True)
    revision = models.CharField(max_length=50, null=True, blank=True)
    who = models.CharField(max_length=100, null=True, blank=True,
                           db_index=True)
    files = models.ManyToManyField(File)
    comments = models.TextField(null=True, blank=True)
    when = models.DateTimeField()
    tags = models.ManyToManyField(Tag)

    class Meta:
        unique_together = (('number', 'master'),)

    def __unicode__(self):
        rv = u'Change %d' % self.number
        if self.branch:
            rv += ', ' + self.branch
        if self.tags:
            rv += u' (%s)' % ', '.join(map(unicode, self.tags.all()))
        return rv


class Change_Tags(models.Model):
    """Helper model for change.tags queries.

    This model maps the ManyToManyField between Tag and Change,
    and does not create any database entries itself, thanks to
    Meta.managed = False.
    """
    change = models.ForeignKey(Change)
    tag = models.ForeignKey(Tag)

    class Meta:
        unique_together = (('change', 'tag'),)
        managed = False


class SourceStamp(models.Model):
    changes = models.ManyToManyField(Change, through='NumberedChange',
                                     related_name='stamps')
    branch = models.CharField(max_length=100, null=True, blank=True)
    revision = models.CharField(max_length=50, null=True, blank=True)


class NumberedChange(models.Model):
    change = models.ForeignKey(Change, related_name='numbered_changes')
    sourcestamp = models.ForeignKey(SourceStamp,
                                    related_name='numbered_changes')
    number = models.IntegerField(db_index=True)


# this is needed inside the Meta class of the Property class but because we're
# not allowed to creat variables inside the class itself, we figure out what
# database engine we're using *before* defining the Property class.
try:
    database_engine = settings.DATABASES['default']['ENGINE']
except KeyError:
    database_engine = settings.DATABASE_ENGINE


class Property(models.Model):
    """Helper model for build properties.

    To support complex property values, they are internally pickled.
    """
    name = models.CharField(max_length=20, db_index=True)
    source = models.CharField(max_length=20, db_index=True)
    value = fields.PickledObjectField(null=True, blank=True)

    class Meta:
        if not database_engine.endswith('mysql'):
            # hack around mysql, that doesn't do unique of unconstrained texts
            unique_together = (('name', 'source', 'value'),)

    def __unicode__(self):
        return "%s: %s" % (self.name, self.value)


class Builder(models.Model):
    """Model for buildbot.status.builder.BuilderStatus"""
    name = models.CharField(max_length=50, unique=True, db_index=True)
    master = models.ForeignKey(Master, related_name='builders')
    category = models.CharField(max_length=30, null=True, blank=True,
                                db_index=True)
    bigState = models.CharField(max_length=30, null=True, blank=True)

    def __unicode__(self):
        return u'Builder <%s>' % self.name


class Build(models.Model):
    """Model for buildbot..status.builder.Build
    """
    buildnumber = models.IntegerField(null=True, db_index=True)
    properties = models.ManyToManyField(Property, related_name='builds')
    builder = models.ForeignKey(Builder, related_name='builds')
    slave = models.ForeignKey(Slave, null=True, blank=True)
    starttime = models.DateTimeField(null=True, blank=True)
    endtime = models.DateTimeField(null=True, blank=True)
    result = models.SmallIntegerField(null=True, blank=True)
    reason = models.CharField(max_length=50, null=True, blank=True)
    sourcestamp = models.ForeignKey(SourceStamp, null=True,
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
            raise Property.DoesNotExist(name)
        except Property.DoesNotExist:
            prop, created = Property.objects.get_or_create(name=name,
                                                           source=source,
                                                           value=value)
        self.properties.add(prop)
        self.save()

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
        l = [(p.name, p.value, p.source) for p in self.properties.iterator()]
        # hardcode buildername and buildnumber again
        l += [('buildername', self.builder.name, 'Build'),
              ('buildnumber', self.buildnumber, 'Build')]
        l.sort()
        return l

    def __unicode__(self):
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
    build = models.ForeignKey(Build, related_name='steps')


class URL(models.Model):
    name = models.CharField(max_length=20)
    url = models.URLField()
    step = models.ForeignKey(Step, related_name='urls')


class Log(models.Model):
    name = models.CharField(max_length=100, null=True, blank=True)
    filename = models.CharField(max_length=200, unique=True,
                                null=True, blank=True)
    step = models.ForeignKey(Step, related_name='logs')
    isFinished = models.BooleanField(default=False)
    html = models.TextField(null=True, blank=True)

    def __unicode__(self):
        if self.filename:
            return self.filename
        return 'HTMLLog %d' % self.id


class BuildRequest(models.Model):
    """Buildrequest status model"""
    builder = models.ForeignKey(Builder)
    submitTime = models.DateTimeField()
    builds = models.ManyToManyField(Build, related_name='requests')
    sourcestamp = models.ForeignKey(SourceStamp, related_name='requests')
