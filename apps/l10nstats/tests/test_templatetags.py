# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
from __future__ import absolute_import
from __future__ import unicode_literals

from elmo.test import TestCase
from django.utils.safestring import SafeText
from ..models import Run
from ..templatetags.run_filters import showrun
from html5lib import parseFragment


class ShowRunTestCase(TestCase):

    def test_errors(self):
        r = Run(errors=3)
        r.id = 1
        rv = showrun(r)
        self.assertIsInstance(rv, SafeText)
        frag = parseFragment(rv)
        childNodes = list(frag)
        self.assertEqual(len(childNodes), 1)
        a = childNodes[0]
        self.assertDictEqual(
            a.attrib, {'data-errors': '3',
                       'data-total': '0',
                       'data-missing': '0',
                       'href': '/dashboard/compare?run=1',
                       'data-warnings': '0'})
        text = a.text
        self.assertTrue('3' in text and 'error' in text)

    def test_missing(self):
        r = Run(missing=3)
        r.id = 1
        rv = showrun(r)
        self.assertIsInstance(rv, SafeText)
        frag = parseFragment(rv)
        childNodes = list(frag)
        self.assertEqual(len(childNodes), 1)
        a = childNodes[0]
        self.assertDictEqual(
            a.attrib, {'data-errors': '0',
                       'data-total': '0',
                       'data-missing': '3',
                       'href': '/dashboard/compare?run=1',
                       'data-warnings': '0'})
        text = a.text
        self.assertTrue('3' in text and 'missing' in text)

    def test_missingInFiles(self):
        r = Run(missingInFiles=3)
        r.id = 1
        rv = showrun(r)
        self.assertIsInstance(rv, SafeText)
        frag = parseFragment(rv)
        childNodes = list(frag)
        self.assertEqual(len(childNodes), 1)
        a = childNodes[0]
        self.assertDictEqual(
            a.attrib, {'data-errors': '0',
                       'data-total': '0',
                       'data-missing': '3',
                       'href': '/dashboard/compare?run=1',
                       'data-warnings': '0'})
        text = a.text
        self.assertTrue('3' in text and 'missing' in text)

    def test_warnings(self):
        r = Run(warnings=3)
        r.id = 1
        rv = showrun(r)
        self.assertIsInstance(rv, SafeText)
        frag = parseFragment(rv)
        childNodes = list(frag)
        self.assertEqual(len(childNodes), 1)
        a = childNodes[0]
        self.assertDictEqual(
            a.attrib, {'data-errors': '0',
                       'data-total': '0',
                       'data-missing': '0',
                       'href': '/dashboard/compare?run=1',
                       'data-warnings': '3'})
        text = a.text
        self.assertTrue('3' in text and 'warning' in text)

    def test_obsolete(self):
        r = Run(obsolete=3)
        r.id = 1
        rv = showrun(r)
        self.assertIsInstance(rv, SafeText)
        frag = parseFragment(rv)
        childNodes = list(frag)
        self.assertEqual(len(childNodes), 1)
        a = childNodes[0]
        self.assertDictEqual(
            a.attrib, {'data-errors': '0',
                       'data-total': '0',
                       'data-missing': '0',
                       'href': '/dashboard/compare?run=1',
                       'data-warnings': '0'})
        text = a.text
        self.assertTrue('3' in text and 'obsolete' in text)

    def test_green(self):
        r = Run()
        r.id = 1
        rv = showrun(r)
        self.assertIsInstance(rv, SafeText)
        frag = parseFragment(rv)
        childNodes = list(frag)
        self.assertEqual(len(childNodes), 1)
        a = childNodes[0]
        self.assertDictEqual(
            a.attrib, {'data-errors': '0',
                       'data-total': '0',
                       'data-missing': '0',
                       'href': '/dashboard/compare?run=1',
                       'data-warnings': '0'})
        text = a.text
        self.assertIn('green', text)
