# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

'''Models representing Applications, Versions, Milestones and information
which locales shipped in what.
'''
from __future__ import absolute_import
from __future__ import unicode_literals

import datetime
from django.db import models
from django.forms import ModelForm
from django.contrib.auth.models import User
from django.utils.encoding import python_2_unicode_compatible
from l10nstats.models import Run
from life.models import Tree, Locale, Push
from elmo_commons.models import DurationThrough


@python_2_unicode_compatible
class Application(models.Model):
    """ stores applications
    """
    name = models.CharField(max_length=50)
    code = models.CharField(max_length=30)

    def __str__(self):
        return self.name


@python_2_unicode_compatible
class AppVersionTreeThrough(DurationThrough):
    appversion = models.ForeignKey('AppVersion', on_delete=models.CASCADE,
                                   related_name='trees_over_time')
    tree = models.ForeignKey(Tree, on_delete=models.CASCADE,
                             related_name='appvers_over_time')

    def __str__(self):
        rv = '{} \u2014 {}'.format(self.appversion, self.tree)
        if self.start or self.end:
            rv += ' [{}:{}]'.format(
                self.start.date() if self.start else '',
                self.end.date if self.end else ''
            )
        return rv

    class Meta(DurationThrough.DurationMeta):
        unique_together = (DurationThrough.unique + ('appversion', 'tree'),)


class AppVersionManager(models.Manager):
    def get_by_natural_key(self, code):
        return self.get(code=code)


@python_2_unicode_compatible
class AppVersion(models.Model):
    """ stores application versions
    """
    objects = AppVersionManager()
    app = models.ForeignKey(Application, on_delete=models.CASCADE)
    version = models.CharField(max_length=10)
    code = models.CharField(max_length=20, blank=True)
    codename = models.CharField(max_length=30, blank=True, null=True)
    trees = models.ManyToManyField(Tree, through=AppVersionTreeThrough)
    # with rapid releases, we're using sign-offs from previous appversion
    fallback = models.ForeignKey('self', blank=True, null=True,
                                 default=None,
                                 on_delete=models.SET_NULL,
                                 related_name='followups')
    accepts_signoffs = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = '%s%s' % (self.app.code, self.version)
        super(AppVersion, self).save(*args, **kwargs)

    def __str__(self):
        return '%s %s' % (self.app.name, self.version)

    def natural_key(self):
        return (self.code,)


@python_2_unicode_compatible
class Signoff(models.Model):
    push = models.ForeignKey(Push, on_delete=models.CASCADE)
    appversion = models.ForeignKey(AppVersion, related_name='signoffs',
                                   on_delete=models.CASCADE)
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    when = models.DateTimeField('signoff timestamp',
                                default=datetime.datetime.utcnow)
    locale = models.ForeignKey(Locale, on_delete=models.CASCADE)

    class Meta:
        permissions = (('review_signoff', 'Can review a Sign-off'),)

    @property
    def accepted(self):
        return self.status == Action.ACCEPTED

    @property
    def status(self):
        try:
            actions = Action.objects.filter(signoff=self).order_by('-pk')
            return actions.values_list('flag', flat=True)[0]
        except IndexError:
            return Action.PENDING

    @property
    def flag(self):
        return dict(Action._meta.get_field('flag').flatchoices)[self.status]

    def __str__(self):
        return ('Signoff for %s %s by %s [%s]' %
                (self.appversion, self.locale.code, self.author, self.when))


@python_2_unicode_compatible
class Action(models.Model):
    """Action implements status changes for sign-offs.
    """
    PENDING, ACCEPTED, REJECTED, CANCELED, OBSOLETED = range(5)
    FLAG_CHOICES = (
        (PENDING, 'pending'),
        (ACCEPTED, 'accepted'),
        (REJECTED, 'rejected'),
        (CANCELED, 'canceled'),
        (OBSOLETED, 'obsoleted'),
    )
    signoff = models.ForeignKey(Signoff, on_delete=models.CASCADE)
    flag = models.IntegerField(choices=FLAG_CHOICES)
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    when = models.DateTimeField('signoff action timestamp',
                                default=datetime.datetime.utcnow)
    comment = models.TextField(blank=True, null=True)

    def __str__(self):
        return ('%s action for [Signoff %s] by %s [%s]' %
                (self.get_flag_display(), self.signoff.id,
                 self.author, self.when))


TEST_CHOICES = (
    (0, Run),
)


class SnapshotManager(models.Manager):
    def create(self, **kwargs):
        if 'test' in kwargs and not isinstance(kwargs['test'], int):
            for i in TEST_CHOICES:
                kwargs['test'] = i[0]
                break
        super(SnapshotManager, self).create(**kwargs)


class Snapshot(models.Model):
    signoff = models.ForeignKey(Signoff, on_delete=models.CASCADE)
    test = models.IntegerField(choices=TEST_CHOICES)
    tid = models.IntegerField()
    objects = SnapshotManager()

    def instance(self):
        for i in TEST_CHOICES:
            if i[0] == self.test:
                return i[1].objects.get(id=self.tid)


STATUS_CHOICES = (
    (0, 'upcoming'),
    (1, 'open'),
    (2, 'shipped'),
)


class SignoffForm(ModelForm):
    class Meta:
        model = Signoff
        fields = ('push',)


class ActionForm(ModelForm):
    class Meta:
        model = Action
        fields = ('signoff', 'flag', 'author', 'comment')
