from django.db import models

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

class Repository(models.Model):
    """stores repository list
    """
    name = models.CharField(max_length = 50)
    url = models.URLField()

    def __unicode__(self):
        return self.name

class Tree(models.Model):
    """stores unique repositories combination like
    comm-central + mozilla-central = Thunderbird trunk
    releases/mozilla-1.9.1 = Firefox 3.5
    mobile-browser + releases/mozilla-1.9.1 = Fennec 1.0
    """
    code = models.CharField(max_length = 50)
    repositories = models.ManyToManyField(Repository)

    def __unicode__(self):
        return self.code
