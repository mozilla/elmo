from django.db import models
from django.conf import settings

class Locale(models.Model):
    """stores list of locales and their names
    code - locale code
    name - english name of the locale
    native - native name in locale's script
    """
    code = models.CharField(max_length = 30, unique = True)
    name = models.CharField(max_length = 100, blank = True, null = True)
    native = models.CharField(max_length = 100, blank = True, null = True)

    def __unicode__(self):
        if self.name:
            return '%s (%s)' % (self.name, self.code)
        else:
            return self.code


class Forest(models.Model):
    name = models.CharField(max_length=100, unique=True)
    url = models.URLField()
    class Meta:
        db_table = 'pushes_forest'
    def __unicode__(self):
        return self.name


class Repository(models.Model):
    name = models.CharField(max_length=100, unique=True)
    url = models.URLField()
    forest = models.ForeignKey(Forest, null=True, blank=True)
    class Meta:
        db_table = 'pushes_repository'
    def last_known_push(self):
        try:
            return self.push_set.order_by('-push_id')[0].push_id
        except IndexError:
            # no push in repo, return 0
            return 0
    def __unicode__(self):
        return self.name


class Push(models.Model):
    repository = models.ForeignKey(Repository)
    user = models.CharField(max_length=200, db_index=True)
    push_date = models.DateTimeField('date of push', db_index=True)
    push_id = models.PositiveIntegerField(default=0)
    class Meta:
        db_table = 'pushes_push'
    
    def __unicode__(self):
        return 'Push to %s by %s [%s]' % (self.repository.name, self.user, self.push_date)

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
    push = models.ForeignKey(Push, related_name='changesets')
    revision = models.CharField(max_length=40, db_index=True)
    user = models.CharField(null = True, blank = True, max_length=100, db_index=True)
    description = models.TextField(null = True, blank = True, db_index=True)
    files = models.ManyToManyField(File)
    class Meta:
        db_table = 'pushes_changeset'
    def url(self):
        return self.push.repository.url + "rev/" + self.revision[:12]
    __unicode__ = url


class Tree(models.Model):
    """stores unique repositories combination like
    comm-central + mozilla-central = Thunderbird trunk
    releases/mozilla-1.9.1 = Firefox 3.5
    mobile-browser + releases/mozilla-1.9.1 = Fennec 1.0
    """
    code = models.CharField(max_length = 50, unique=True)
    repositories = models.ManyToManyField(Repository)
    l10n = models.ForeignKey(Forest)

    def __unicode__(self):
        return self.code
