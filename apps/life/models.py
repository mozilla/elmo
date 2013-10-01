# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

'''Models that represent data present outside of the l10n_site applications,
most notable locales and hg repositories.
'''

from django.db import models
from django.dispatch import receiver
from django.db.models.signals import post_save
from django.core.cache import cache
from mbdb.models import File
File  # silence pyflakes
from elmo_commons.models import DurationThrough


class LocaleManager(models.Manager):
    def get_by_natural_key(self, code):
        return self.get(code=code)


class Locale(models.Model):
    """stores list of locales and their names

    Fields:
    code   -- locale code
    name   -- english name of the locale
    native -- native name in locale's script
    """
    objects = LocaleManager()
    code = models.CharField(max_length=30, unique=True)
    name = models.CharField(max_length=100, blank=True, null=True)
    native = models.CharField(max_length=100, blank=True, null=True)

    def __unicode__(self):
        if self.name:
            return '%s (%s)' % (self.name, self.code)
        else:
            return self.code

    def natural_key(self):
        return (self.code,)


@receiver(post_save, sender=Locale)
def invalidate_homepage_index_cache(sender, **kwargs):
    cache_key = 'homepage.views.index.etag'
    cache.delete(cache_key)


class TeamLocaleThrough(DurationThrough):
    team = models.ForeignKey(Locale, related_name='locales_over_time')
    locale = models.ForeignKey(Locale, related_name='teams_over_time')

    class Meta(DurationThrough.DurationMeta):
        unique_together = (DurationThrough.unique + ('team', 'locale'),)

    def __unicode__(self):
        rv = u'%s \u2014 %s' % (self.team.code, self.locale.code)
        if self.start or self.end:
            rv += u' [%s:%s]' % (
                self.start and str(self.start.date()) or '',
                self.end and str(self.end.date()) or '')
        return rv


class Branch(models.Model):
    """mercurial in-repo branch
    """
    name = models.TextField(help_text="name of the branch")

    def __unicode__(self):
        return self.name


class ChangesetManager(models.Manager):
    def get_by_natural_key(self, rev):
        return self.get(revision__startswith=rev)


class Changeset(models.Model):
    """stores list of changsets

    Fields:
    revision -- revision that has been created by this changeset
    user -- author of this changeset
    description -- description added to this changeset
    files -- files affected by this changeset
    branch -- hg internal branch, defaults to the "default" branch
    parents -- parents of this changeset. Should be either one or two
    """
    objects = ChangesetManager()
    revision = models.CharField(max_length=40, db_index=True, unique=True)
    user = models.CharField(max_length=200, db_index=True, default='')
    description = models.TextField(null=True, default='')
    files = models.ManyToManyField(File)
    branch = models.ForeignKey(Branch, default=1, related_name='changesets')
    parents = models.ManyToManyField("self", symmetrical=False,
                                     related_name='_children')

    @property
    def shortrev(self):
        return self.revision[:12]

    @property
    def children(self):
        return self._children.exclude(revision='0' * 40)

    def url(self):
        try:
            return (self.pushes.order_by('push_date')[0].repository.url
                    + "rev/" + self.shortrev)
        except IndexError:
            pass
        try:
            return self.repositories.all()[0].url + "rev/" + self.shortrev
        except IndexError:
            return "urn:x-changeset:" + self.shortrev

    __unicode__ = url

    def natural_key(self):
        return (self.shortrev,)


class ForestManager(models.Manager):
    def get_by_natural_key(self, name):
        return self.get(name=name)


class Forest(models.Model):
    """stores set of trees

    For example all l10n-central trees create single forest

    Fields:
    name -- name of the forest
    url -- url to the tree list which is a base for a tree url pattern
           (e.g. http://hg.mozilla.org/l10n-central/)
    """
    objects = ForestManager()
    name = models.CharField(max_length=100, unique=True)
    url = models.URLField()

    def __unicode__(self):
        return self.name

    def natural_key(self):
        return (self.name,)


class RepositoryManager(models.Manager):
    def get_by_natural_key(self, name):
        return self.get(name=name)


class Repository(models.Model):
    """stores set of repositories

    Fields:
    name -- name of the repository
    url -- url to the repository
    changesets -- changesets inside this repository
    forest -- forest this repository belongs to. (optional)
              It's only used for repositories that belongs to a forest (l10n)
    """
    objects = RepositoryManager()
    name = models.CharField(max_length=100, unique=True)
    url = models.URLField()
    changesets = models.ManyToManyField(Changeset, related_name='repositories')
    forest = models.ForeignKey(Forest, null=True, blank=True,
                               related_name='repositories')
    locale = models.ForeignKey(Locale, null=True, blank=True)

    def last_known_push(self):
        try:
            return self.push_set.order_by('-push_id')[0].push_id
        except IndexError:
            # no push in repo, return 0
            return 0

    def save(self, *args, **kwargs):
        # do we need an initial changeset? self.id will be set
        # in super().save()
        needsInitialChangeset = self.id is None
        # Call the "real" save() method.
        super(Repository, self).save(*args, **kwargs)
        if needsInitialChangeset:
            cs = Changeset.objects.get(revision='0' * 40)
            self.changesets.add(cs)

    def __unicode__(self):
        return self.name

    def natural_key(self):
        return (self.name,)


class PushManager(models.Manager):
    def get_by_natural_key(self, repo_name, rev):
        return self.get(repository__name=repo_name,
                        changesets__revision__startswith=rev)


class Push(models.Model):
    """stores context of who pushed what when

    Fields:
    repository -- repository changesets were pushed to
    user -- person who did the push
    push_date -- date and time of the push
    push_id -- unique id of the push
    """
    objects = PushManager()
    repository = models.ForeignKey(Repository)
    changesets = models.ManyToManyField(Changeset, related_name="pushes")
    user = models.CharField(max_length=200, db_index=True)
    push_date = models.DateTimeField('date of push', db_index=True)
    push_id = models.PositiveIntegerField(default=0)

    @property
    def tip(self):
        if hasattr(self, '_tip'):
            return getattr(self, '_tip')
        tip = self.changesets.order_by('-pk')[0]
        setattr(self, '_tip', tip)
        return tip

    def __unicode__(self):
        tip = self.tip.shortrev
        return self.repository.url + 'pushloghtml?changeset=' + tip

    def natural_key(self):
        return (self.repository.name, self.tip.shortrev)


class Push_Changesets(models.Model):
    """helper model for queries over the ManyToMany between Push and Changeset.
    Non-managed, thus doesn't affect the db.
    """
    push = models.ForeignKey(Push)
    changeset = models.ForeignKey(Changeset)

    class Meta:
        unique_together = (('push', 'changeset'),)
        managed = False


class TreeManager(models.Manager):
    def get_by_natural_key(self, code):
        return self.get(code=code)


class Tree(models.Model):
    """stores unique repositories combination

    Like:
    comm-central + mozilla-central = Thunderbird trunk
    releases/mozilla-1.9.1 = Firefox 3.5
    mobile-browser + releases/mozilla-1.9.1 = Fennec 1.0

    Fiels:
    code -- unique code name of the tree (e.g. fx35)
    repositories -- list of repositories that make this tree
    l10n -- forest that is assigned to this tree
    """
    objects = TreeManager()
    code = models.CharField(max_length=50, unique=True)
    repositories = models.ManyToManyField(Repository)
    l10n = models.ForeignKey(Forest)

    def __unicode__(self):
        return self.code

    def natural_key(self):
        return (self.code,)
