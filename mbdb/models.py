import pickle

from django.db import models
import fields


class File(models.Model):
    """Model for files throughout"""
    # not  unique = True, mysql doesn't like long unique utf-8 strings
    path = models.CharField(max_length=400, db_index=True)

    def __unicode__(self):
        return self.path


class Tag(models.Model):
    """Model to add tags to the Change model"""
    value = models.CharField(max_length = 50, db_index = True, unique = True)

    def __unicode__(self):
        return self.value


class Change(models.Model):
    """Model for buildbot.changes.changes.Change"""
    number = models.PositiveIntegerField(primary_key = True)
    branch = models.CharField(max_length = 100, null = True, blank = True)
    revision = models.CharField(max_length = 50, null = True, blank = True)
    who = models.CharField(max_length = 100, null = True, blank = True,
                           db_index = True)
    files = models.ManyToManyField(File)
    comments = models.TextField(null = True, blank = True)
    when = models.DateTimeField()
    tags = models.ManyToManyField(Tag)

    def __unicode__(self):
        rv = u'Change %d' % self.number
        if self.branch:
            rv += ', ' + self.branch
        if self.tags:
            rv += u' (%s)' % ', '.join(map(unicode, self.tags.all()))
        return rv


class Property(models.Model):
    """Helper model for build properties.

    To support complex property values, they are internally pickled.
    """
    name            = models.CharField(max_length = 20, db_index = True)
    source          = models.CharField(max_length = 20, db_index = True)
    value           = fields.PickledObjectField(null = True, blank = True,
                                                db_index = True)
    unique_together = (('name', 'source', 'value'),)

    def __unicode__(self):
        return "%s: %s" % (self.name, self.value)


class Builder(models.Model):
    """Model for buildbot.status.builder.BuilderStatus"""
    name     = models.CharField(max_length = 50, unique = True, db_index = True)
    category = models.CharField(max_length = 30, null = True, blank = True,
                                db_index = True)
    bigState = models.CharField(max_length = 30, null = True, blank = True)

    def __unicode__(self):
        return u'Builder <%s>' % self.name


class Build(models.Model):
    """Model for buildbot..status.builder.Build
    """
    buildnumber = models.IntegerField(null = True, db_index = True)
    properties  = models.ManyToManyField(Property, related_name = 'builds')
    builder     = models.ForeignKey(Builder, related_name = 'builds')
    slavename   = models.CharField(max_length = 50, null=True, blank = True)
    starttime   = models.DateTimeField(null = True, blank = True)
    endtime     = models.DateTimeField(null = True, blank = True)
    result      = models.SmallIntegerField(null = True, blank = True)
    reason      = models.CharField(max_length = 50, null = True, blank = True)
    changes     = models.ManyToManyField(Change, null = True,
                                         related_name = 'builds')

    def setProperty(self, name, value, source):
        if name in ('buildername', 'buildnumber'):
            # we have those in the db, ignore
            return
        try:
            # First, see if we have the property, or a property of that name,
            # at least.
            prop = self.properties.get(name = name)
            if prop.value == value and prop.source == source:
                # we already know this, we're done
                return
            if prop.builds.count() < 2:
                # this is our own property, set the new value
                prop.value = value
                prop.source = source
                prop.save()
                return
            # otherwise, unbind the property, and fake a DoesNotExist
            self.properties.remove(prop)
            raise Property.DoesNotExist(name)
        except Property.DoesNotExist:
            prop, created = Property.objects.get_or_create(name = name,
                                                           source = source,
                                                           value = value)
        self.properties.add(prop)
        self.save()

    def getProperty(self, name, default = None):
        if name == 'buildername':
            # hardcode, we know that
            return self.builder.name
        if name == 'buildnumber':
            # hardcode, we know that
            return self.buildnumber
        # all others are real properties, query the db
        try:
            prop = self.properties.get(name = name)
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
    name      = models.CharField(max_length=50)
    text      = fields.ListField(null = True, blank = True)
    text2     = fields.ListField(null = True, blank = True)
    result    = models.SmallIntegerField(null = True, blank = True)
    starttime = models.DateTimeField(null = True, blank = True)
    endtime   = models.DateTimeField(null = True, blank = True)
    build     = models.ForeignKey(Build, related_name = 'steps')


class URL(models.Model):
    name = models.CharField(max_length = 20)
    url = models.URLField()
    step = models.ForeignKey(Step, related_name = 'urls')


class Log(models.Model):
    name = models.CharField(max_length = 100, null = True, blank = True)
    filename = models.CharField(max_length = 200, unique = True,
                                null = True, blank = True)
    step = models.ForeignKey(Step, related_name = 'logs')
    isFinished = models.BooleanField(default = False)
    html = models.TextField(null = True, blank = True)

    def __unicode__(self):
        if self.filename:
            return self.filename
        return 'HTMLLog %d' % self.id

        
