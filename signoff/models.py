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
    code = models.CharField(max_length = 30, blank = True, null = True)
    tree = models.ForeignKey(Tree)

    def __unicode__(self):
        return '%s %s' % (self.app.name, self.version)

class Signoff(models.Model):
    push = models.ForeignKey(Push)
    appversion = models.ForeignKey(AppVersion, related_name = 'signoffs')
    author = models.ForeignKey(User)
    when = models.DateTimeField('signoff timestamp', default=datetime.now)
    locale = models.ForeignKey(Locale)

    @property
    def accepted(self):
        if self.status == 0:
            return True
        else:
            return False

    @property
    def status(self):
        action = Action.objects.filter(signoff=self).order_by('-pk')
        if action:
            return action[0].flag
        else:
            return None

    def __unicode__(self):
        return 'Signoff for %s %s by %s [%s]' % (self.appversion, self.locale.code, self.author, self.when)

FLAG_CHOICES = (
    (0, 'accepted'),
    (1, 'rejected'),
    (2, 'revoked'),
    (3, 'obsoleted'),
)

class Action(models.Model):
    signoff = models.ForeignKey(Signoff)
    flag = models.IntegerField(choices=FLAG_CHOICES)
    author = models.ForeignKey(User)
    when = models.DateTimeField('signoff action timestamp', default=datetime.now)
    comment = models.TextField(blank=True, null=True)

STATUS_CHOICES = (
    (0, 'upcoming'),
    (1, 'open'),
    (2, 'shipped'),
)

class Milestone(models.Model):
    """ stores unique milestones like fx35b4
    The milestone is open for signoff between string_freeze and code
    """
    code = models.CharField(max_length = 30)
    name = models.CharField(max_length = 50, blank = True, null = True)
    appver = models.ForeignKey(AppVersion)
    signoffs = models.ManyToManyField(Signoff, related_name='shipped list', null=True, blank=True)
    status = models.IntegerField(choices=STATUS_CHOICES, default=0)

    def get_start_event(self):
        try:
            return Event.objects.get(type=0, milestone=self)
        except:
            return None

    def get_end_event(self):
        try:
            return Event.objects.get(type=1, milestone=self)
        except:
            return None

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


class SignoffForm(ModelForm):
    class Meta:
        model = Signoff
        fields = ('push',)

class ActionForm(ModelForm):
    class Meta:
        model = Action
        fields = ('signoff','flag','author', 'comment')
