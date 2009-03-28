from django.db import models

from pushes.models import Push
from life.models import Tree

class Milestone(models.Model):
    """ stores unique milestones like fx35b4
    The milestone is open for signoff between string_freeze and code
    """
    code = models.CharField(max_length = 50)
    name = models.CharField(max_length = 50, blank = True, null = True)

    def __init__(self):
        self._start_event = None;
        self._end_event = None;

    def get_start_event(self):
        return Event.objects.get(id=self._start_event)

    def set_start_event(self, event):
        self._start_event = event.id

    def get_end_event(self):
        return Event.objects.get(id=self._end_event)

    def set_end_event(self, event):
        self._end_event = event.id

    start_event = property(get_start_event, set_start_event)
    end_event = property(get_end_event, set_end_event)

    def __unicode__(self):
        return self.name or self.code

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
        return self.name

class Signoff(models.Model):
    revision = models.ForeignKey(Push)
    milestone = models.ForeignKey(Milestone, related_name = 'signoffs')
    author = models.CharField(max_length = 50, blank = True, null = True)
    tree = models.ForeignKey(Tree)

