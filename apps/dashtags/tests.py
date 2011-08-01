from django.test import TestCase
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


class Simile(unittest.TestCase):
    """Test the simile tags to include script tags for exhibit and timeplot."""

    def test_exhibit(self):
        t = template.Template("{% load simile %} {% exhibit %}")
        c = template.Context({})
        out = t.render(c)
        self.assertTrue("exhibit-api.js" in out,
                        "exhibit-api.js is not in " + out)
        self.assertTrue("simile-ajax-api.js" in out,
                        "simile-ajax-api.js is not in " + out)

    def test_timeplot(self):
        t = template.Template("{% load simile %} {% timeplot %}")
        c = template.Context({})
        out = t.render(c)
        self.assertTrue("timeplot-api.js" in out,
                        "timeplot-api.js is not in " + out)
        self.assertTrue("timeline-api.js" in out,
                        "timeline-api.js is not in " + out)
        self.assertTrue("simile-ajax-api.js" in out,
                        "simile-ajax-api.js is not in " + out)
