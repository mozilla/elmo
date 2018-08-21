# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""Django template filters for use in any app in the project"""
from __future__ import absolute_import
from __future__ import unicode_literals

from django import template
from django.utils.safestring import mark_safe
import bleach

register = template.Library()


@register.filter
def bleach_safe(text, autoescape=None):
    return mark_safe(bleach.linkify(bleach.clean(text)))
bleach_safe.needs_autoescape = False  # noqa
