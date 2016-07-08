# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""Django template filters for use in any app in the project"""
from __future__ import absolute_import

from django import template
from django.utils.safestring import mark_safe

register = template.Library()

@register.simple_tag
def expression(expr):
    return mark_safe("{{ " + expr + " }}")
