# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

'''Models representing privacy policies and how they change over time.
'''
from __future__ import absolute_import
from __future__ import unicode_literals

from django.db import models
from django.utils.encoding import python_2_unicode_compatible
from django.utils.html import strip_tags
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType


class CTMixin(object):
    """Mixin to create a cached query for the ContentType for this model.
    """
    _ct = None

    @classmethod
    def contenttype(cls):
        if cls._ct is None:
            cls._ct = ContentType.objects.get_for_model(cls)
        return cls._ct


@python_2_unicode_compatible
class Policy(models.Model, CTMixin):
    """A privacy

    The history is stored with LogEntry objects, which is handled in the
    views modifying the policy. Edits to the policy are stored by a separate
    db entry each.
    """
    text = models.TextField(help_text='''use html markup''')
    active = models.BooleanField(default=False)

    class Meta:
        permissions = (('activate_policy', 'Can activate a policy'),)

    def __str__(self):
        return "%d" % self.id


@python_2_unicode_compatible
class Comment(models.Model, CTMixin):
    """Comments on a policy.
    """
    text = models.TextField()
    policy = models.ForeignKey(Policy, related_name="comments",
                               on_delete=models.CASCADE)
    who = models.ForeignKey(User, related_name="privacy_comments",
                            on_delete=models.CASCADE)

    def __str__(self):
        return strip_tags(self.text)[:20]
