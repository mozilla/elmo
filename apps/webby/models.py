# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from django.db import models
from life.models import Locale
from django.contrib.auth.models import User


class ProjectManager(models.Manager):
    def active(self):
        return self.filter(is_archived=False)


class ProjectType(models.Model):
    """ stores type of the project (PHP, Django, etc.)
    """
    name = models.CharField(max_length=80)

    def __unicode__(self):
        return self.name


class Project(models.Model):
    """ stores projects
    """
    name = models.CharField(max_length=80)
    slug = models.SlugField(max_length=80)
    description = models.TextField()
    is_archived = models.BooleanField(default=False)
    verbatim_url = models.CharField(max_length=150, blank=True, null=True)
    l10n_repo_url = models.CharField(max_length=150, blank=True, null=True)
    code_repo_url = models.CharField(max_length=150, blank=True, null=True)
    stage_url = models.URLField(blank=True, null=True, verify_exists=False)
    final_url = models.URLField(blank=True, null=True, verify_exists=False)
    # stage_auth_url can't be a URLField, because Django doesn't accept the
    # //<user>:<password>@<host>:<port>/<url-path> syntax as valid
    stage_auth_url = models.CharField(max_length=250, blank=True, null=True)
    stage_login = models.CharField(max_length=80, blank=True, null=True)
    stage_passwd = models.CharField(max_length=80, blank=True, null=True)
    locales = models.ManyToManyField(Locale, blank=True, through='Weblocale')
    string_count = models.IntegerField(default=0)
    word_count = models.IntegerField(default=0)
    type = models.ForeignKey(ProjectType)

    objects = ProjectManager()

    def __unicode__(self):
        return self.name


class Weblocale(models.Model):
    """Many-to-Many proxy class for project/locale pairs."""
    class Meta:
        unique_together = (("project", "locale"),)

    project = models.ForeignKey(Project)
    locale = models.ForeignKey(Locale)
    requestee = models.ForeignKey(User, blank=True, null=True)
    in_verbatim = models.BooleanField(default=False)
    in_vcs = models.BooleanField(default=False)
    is_on_stage = models.BooleanField(default=False)
    is_on_prod = models.BooleanField(default=False)

    def __unicode__(self):
        return "%s (%s)" % (self.project.name, self.locale.code)
