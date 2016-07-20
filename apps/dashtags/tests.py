# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
from __future__ import absolute_import

from elmo.test import TestCase
import unittest
from django import template


class Recurse(TestCase):
    """Test the three tags for recursive templates, recurse, recurse_children,
    endrecurse."""
    # no fixtures = []
    def test_recurse(self):
        t = template.Template("""{% load recurse %}{% recurse_children %}
{% for item in items %}{{ item.value }}
{% if item.children %}{% recurse item.children as items %}{% endif %}
{% endfor %}{% endrecurse %}""")
        d = {"items":
             [{
                 "value": "root",
                 "children": [
                     {
                         "value": " leaf1",
                         "children": [{
                             "value": "  leafleaf1"
                             }]
                         },
                     {
                         "value": " leaf2"
                         }
                     ]
                 }
              ]}
        c = template.Context(d)
        out = t.render(c)
        self.assertEqual(out,
          u'\nroot\n\n leaf1\n\n  leafleaf1\n\n\n leaf2\n\n\n')
