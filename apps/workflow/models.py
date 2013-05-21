# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from datetime import datetime

from django.db import models
from life.models import Locale

class Actor(models.Model):
    name = models.CharField(max_length=140)


class ProtoProcess(models.Model):
    summary = models.CharField(max_length=140)
    parent = models.ManyToManyField('self', symmetrical=False,
                                    through='Nesting',
                                    related_name='children')


class Nesting(models.Model):
    '''Nestings store the relationships between ProtoProcesses.'''
    parent = models.ForeignKey(ProtoProcess, related_name="nestings_where_parent")
    child = models.ForeignKey(ProtoProcess, related_name="nestings_where_child")
    order = models.PositiveIntegerField()


class ProtoTask(models.Model):
    summary = models.CharField(max_length=140)
    # `process` should only by `null` while setting it up
    process = models.ForeignKey(ProtoProcess, related_name='steps',
                                null=True, blank=True)
    template = models.TextField()
    
    
class ProtoStep(models.Model):
    summary = models.CharField(max_length=140)
    task = models.ForeignKey(ProtoTask, related_name='steps')
    parent = models.ForeignKey('self', related_name='children',
                               null=True, blank=True)
    order = models.PositiveIntegerField()
    owner = models.ForeignKey(Actor, related_name='protosteps')


class Process(models.Model):
    '''Processes provide hierachies for Tasks'''
    proto = models.ForeignKey(ProtoProcess, related_name='instances')
    locale = models.ForeignKey(Locale, related_name='processes')
    summary = models.CharField(max_length=140)
    created = models.DateTimeField(default=datetime.utcnow)

    
class Task(models.Model):
    '''Tasks correspond to bugs in bugzilla'''
    proto = models.ForeignKey(ProtoTask, related_name='instances')
    summary = models.CharField(max_length=140)
    created = models.DateTimeField(default=datetime.utcnow)
    bug = models.PositiveIntegerField(null=True, blank=True)
    data = models.TextField()


class Step(models.Model):
    '''Steps model processes within a bug that don't warrant
    a bug on their own'''
    proto = models.ForeignKey(ProtoStep, related_name='instances')
    task = models.ForeignKey(Task, related_name='steps')
    summary = models.CharField(max_length=140)
    created = models.DateTimeField(default=datetime.utcnow)
    resolved = models.BooleanField()
