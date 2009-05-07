from django.db import models
from django.forms import ModelForm, Select
from django.contrib.auth.models import User

from life.models import Tree, Locale, Push

from datetime import datetime

class Application(models.Model):
    """ stores applications
    """
    name = models.CharField(max_length = 50)
    code = models.CharField(max_length = 30)

    def __unicode__(self):
        return self.name

class AppVersion(models.Model):
    """ stores application versions
    """
    app = models.ForeignKey(Application)
    version = models.CharField(max_length = 10)
    codename = models.CharField(max_length = 30, blank = True, null = True)
    tree = models.ForeignKey(Tree)

    def __unicode__(self):
        return '%s %s' % (self.app.name, self.version)


class Milestone(models.Model):
    """ stores unique milestones like fx35b4
    The milestone is open for signoff between string_freeze and code
    """
    code = models.CharField(max_length = 30)
    name = models.CharField(max_length = 50, blank = True, null = True)
    appver = models.ForeignKey(AppVersion)

    def get_start_event(self):
        return Event.objects.get(type=0, milestone=self) or None

    def get_end_event(self):
        return Event.objects.get(type=1, milestone=self) or None

    start_event = property(get_start_event)
    end_event = property(get_end_event)

    def __unicode__(self):
        if self.name:
            return '%s %s %s' % (self.appver.app.name, self.appver.version, self.name)
        else:
            return self.code

TYPE_CHOICES = (
    (0, 'signoff start'),
    (1, 'signoff end'),
)

class Event(models.Model):
    name = models.CharField(max_length = 50)
    type = models.IntegerField(choices=TYPE_CHOICES)
    date = models.DateField()
    milestone = models.ForeignKey(Milestone, related_name='events')

    def __unicode__(self):
        return '%s for %s (%s)' % (self.name, self.milestone, self.date)

class Signoff(models.Model):
    push = models.ForeignKey(Push)
    milestone = models.ForeignKey(Milestone, related_name = 'signoffs')
    author = models.ForeignKey(User)
    when = models.DateTimeField('signoff timestamp', default=datetime.now)
    locale = models.ForeignKey(Locale)
    accepted = models.NullBooleanField()

    def __unicode__(self):
        return 'Signoff for %s %s by %s [%s]' % (self.milestone, self.locale.code, self.author, self.when.strftime("%Y-%m-%d %H:%M"))

class SignoffForm(ModelForm):
    class Meta:
        model = Signoff
        fields = ('push',)

class AcceptForm(ModelForm):
    class Meta:
        model = Signoff
        fields = ('accepted',)
