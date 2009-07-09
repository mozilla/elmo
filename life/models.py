from django.db import models
from django.conf import settings

class Locale(models.Model):
    """stores list of locales and their names
    
    Fields:
    code -- locale code
    name -- english name of the locale
    native -- native name in locale's script
    """
    code = models.CharField(max_length = 30, unique = True)
    name = models.CharField(max_length = 100, blank = True, null = True)
    native = models.CharField(max_length = 100, blank = True, null = True)

    def __unicode__(self):
        if self.name:
            return '%s (%s)' % (self.name, self.code)
        else:
            return self.code


class Branch(models.Model):
    """mercurial in-repo branch
    """
    name = models.TextField(help_text="name of the branch")
    def __unicode__(self):
        return self.name


class Forest(models.Model):
    """stores set of trees
    
    For example all l10n-central trees create single forest
    
    Fields:
    name -- name of the forest
    url -- url to the tree list which is a base for a tree url pattern
           (e.g. http://hg.mozilla.org/l10n-central/)
    """
    name = models.CharField(max_length=100, unique=True)
    url = models.URLField()
    def __unicode__(self):
        return self.name


class Repository(models.Model):
    """stores set of repositories
    
    Fields:
    name -- name of the repository
    url -- url to the repository
    forest -- forest this repository belongs to. (optional)
              It's only used for repositories that belongs to a forest (l10n)
    """
    name = models.CharField(max_length=100, unique=True)
    url = models.URLField()
    forest = models.ForeignKey(Forest, null=True, blank=True,
                               related_name='repositories')
    locale = models.ForeignKey(Locale, null=True, blank=True)
    def last_known_push(self):
        try:
            return Push.objects.filter(changesets__repository=self).order_by('-push_id').values_list('push_id', flat=True)[0]
        except IndexError:
            # no push in repo, return 0
            return 0
    def save(self, force_insert=False, force_update=False):
        needsInitialChangeset = self.id is None
        # Call the "real" save() method.
        super(Repository, self).save(force_insert, force_update)
        if needsInitialChangeset:
            cs = Changeset(repository=self,
                           revision='0'*40)
            cs.save()
            cs.parents.add(cs)
            cs.save()
    def __unicode__(self):
        return self.name


class Push(models.Model):
    """stores list of revisions pushed to repositories
    
    Fields:
    user -- person who did the push
    push_date -- date and time of the push
    push_id -- unique id of the push
    """
    user = models.CharField(max_length=200, db_index=True)
    push_date = models.DateTimeField('date of push', db_index=True)
    push_id = models.PositiveIntegerField(default=0)

    @property
    def tip(self):
        return self.changesets.order_by('-pk')[0]

    def __unicode__(self):
        tip = self.tip.shortrev
        return self.tip.repository.url + 'pushloghtml?changeset=' + tip
        #return 'Push to %s by %s [%s]' % (self.repository.name, self.user, self.push_date)

if 'mbdb' in settings.INSTALLED_APPS:
    from mbdb.models import File
else:
    class File(models.Model):
        class Meta:
            db_table = 'mbdb_file'
        path = models.CharField(max_length=400, db_index=True)
        def __unicode__(self):
            return self.path


class Changeset(models.Model):
    """stores list of changsets
    
    Fields:
    repository -- repository of this revision
    push -- push this changeset is part of (if not 000000000000)
    revision -- revision that has been created by this changeset
    user -- author of this changeset
    description -- description added to this changeset
    files -- files affected by this changeset
    """
    repository = models.ForeignKey(Repository, related_name='changesets')
    push = models.ForeignKey(Push, related_name='changesets',
                             null=True, blank=True)
    revision = models.CharField(max_length=40, db_index=True)
    user = models.CharField(max_length=200, db_index=True, default='')
    description = models.TextField(null = True, default='')
    files = models.ManyToManyField(File)
    branch = models.ForeignKey(Branch, default=1, related_name='changesets')
    parents = models.ManyToManyField("self", symmetrical=False,
                                     related_name='_children')

    @property
    def shortrev(self):
        return self.revision[:12]

    @property
    def children(self):
        return self._children.exclude(revision=40*'0')

    def url(self):
        return self.repository.url + "rev/" + self.shortrev
    __unicode__ = url


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
    code = models.CharField(max_length = 50, unique=True)
    repositories = models.ManyToManyField(Repository)
    l10n = models.ForeignKey(Forest)

    def __unicode__(self):
        return self.code
