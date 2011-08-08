# ***** BEGIN LICENSE BLOCK *****
# Version: MPL 1.1/GPL 2.0/LGPL 2.1
#
# The contents of this file are subject to the Mozilla Public License Version
# 1.1 (the "License"); you may not use this file except in compliance with
# the License. You may obtain a copy of the License at
# http://www.mozilla.org/MPL/
#
# Software distributed under the License is distributed on an "AS IS" basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied. See the License
# for the specific language governing rights and limitations under the
# License.
#
# The Original Code is l10n django site.
#
# The Initial Developer of the Original Code is
# Mozilla Foundation.
# Portions created by the Initial Developer are Copyright (C) 2011
# the Initial Developer. All Rights Reserved.
#
# Contributor(s):
#   Zbigniew Braniecki <gandalf@mozilla.com>
#
# Alternatively, the contents of this file may be used under the terms of
# either the GNU General Public License Version 2 or later (the "GPL"), or
# the GNU Lesser General Public License Version 2.1 or later (the "LGPL"),
# in which case the provisions of the GPL or the LGPL are applicable instead
# of those above. If you wish to allow use of your version of this file only
# under the terms of either the GPL or the LGPL, and not to allow others to
# use your version of this file under the terms of the MPL, indicate your
# decision by deleting the provisions above and replace them with the notice
# and other provisions required by the GPL or the LGPL. If you do not delete
# the provisions above, a recipient may use your version of this file under
# the terms of any one of the MPL, the GPL or the LGPL.
#
# ***** END LICENSE BLOCK *****

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
