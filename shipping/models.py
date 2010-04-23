from django.db import models
from django.forms import ModelForm, Select
from django.contrib.auth.models import User
from l10nstats.models import Run
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
    code = models.CharField(max_length = 20, blank = True)
    codename = models.CharField(max_length = 30, blank = True, null = True)
    tree = models.ForeignKey(Tree)


    def save(self):
        if not self.code:
            self.code = '%s%s' % (self.app.code, self.version)
        super(AppVersion, self).save()

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
        return self.status == 1

    @property
    def status(self):
        try:
            actions = Action.objects.filter(signoff=self).order_by('-pk')
            return actions.values_list('flag', flat=True)[0]
        except IndexError:
            return 0

    @property
    def flag(self):
        return dict(Action._meta.get_field('flag').flatchoices)[self.status]

    def __unicode__(self):
        return 'Signoff for %s %s by %s [%s]' % (self.appversion, self.locale.code, self.author, self.when)

FLAG_CHOICES = (
    (0, 'pending'),
    (1, 'accepted'),
    (2, 'rejected'),
    (3, 'revoked'),
    (4, 'obsoleted'),
)

class Action(models.Model):
    signoff = models.ForeignKey(Signoff)
    flag = models.IntegerField(choices=FLAG_CHOICES)
    author = models.ForeignKey(User)
    when = models.DateTimeField('signoff action timestamp', default=datetime.now)
    comment = models.TextField(blank=True, null=True)

    def __unicode__(self):
        return '%s action for [Signoff %s] by %s [%s]' % (self.get_flag_display(), self.signoff.id, self.author, self.when)

TEST_CHOICES = (
    (0, Run),
)

class SnapshotManager(models.Manager):
    def create(self, **kwargs):
        if 'test' in kwargs and not isinstance(kwargs['test'], int):
            for i in TEST_CHOICES:
                kwargs['test']=i[0]
                break
        super(SnapshotManager, self).create(**kwargs)

class Snapshot(models.Model):
    signoff = models.ForeignKey(Signoff)
    test = models.IntegerField(choices=TEST_CHOICES)
    tid = models.IntegerField()
    objects = SnapshotManager()

    def instance(self):
        for i in TEST_CHOICES:
            if i[0]==self.test:
                return i[1].objects.get(id=self.tid)

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
    name = models.CharField(max_length = 50)
    appver = models.ForeignKey(AppVersion)
    signoffs = models.ManyToManyField(Signoff, related_name='shipped_in', null=True, blank=True)
    status = models.IntegerField(choices=STATUS_CHOICES, default=0)
    class Meta:
        permissions = (('can_open', 'Can open a Milestone for sign-off'),
                       ('can_ship', 'Can ship a Milestone'))

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
        if self.name is not None:
            frags = [self.appver.app.name, self.appver.version]
            if self.name:
                frags.append(self.name)
            return ' '.join(frags)
        else:
            return self.code


class Milestone_Signoffs(models.Model):
    """Helper model to query milestone.signoffs.

    The model doesn't alter the schema and is set up such that it
    can be used to create rich queries on Milestone/Signoff mappings.
    """
    milestone = models.ForeignKey(Milestone)
    signoff = models.ForeignKey(Signoff)
    class Meta:
        unique_together = (('milestone','signoff'),)
        managed = False


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
