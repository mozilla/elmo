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
# Portions created by the Initial Developer are Copyright (C) 2010
# the Initial Developer. All Rights Reserved.
#
# Contributor(s):
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

'''Models representing privacy policies and how they change over time.
'''

from django.db import models
from django.utils.html import strip_tags
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType


class CTMixin:
    """Mixin to create a cached query for the ContentType for this model.
    """
    _ct = None

    @classmethod
    def contenttype(cls):
        if cls._ct is None:
            cls._ct = ContentType.objects.get_for_model(cls)
        return cls._ct


class Policy(models.Model, CTMixin):
    """A privacy

    The history is stored with LogEntry objects, which is handled in the
    views modifying the policy. Edits to the policy are stored by a separate
    db entry each.
    """
    text = models.TextField(help_text='''use html markup''')
    active = models.BooleanField()

    class Meta:
        permissions = (('activate_policy', 'Can activate a policy'),)

    def __unicode__(self):
        return "%d" % self.id


class Comment(models.Model, CTMixin):
    """Comments on a policy.
    """
    text = models.TextField()
    policy = models.ForeignKey(Policy, related_name="comments")
    who = models.ForeignKey(User, related_name="privacy_comments")

    def __unicode__(self):
        return strip_tags(self.text)[:20]
