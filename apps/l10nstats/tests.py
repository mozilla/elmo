# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
from __future__ import absolute_import
from __future__ import unicode_literals

import datetime
from six.moves.urllib.parse import urlparse
from elmo.test import TestCase
from django.http import QueryDict
from django.core.urlresolvers import reverse
from django.utils.encoding import force_text
from django.utils.safestring import SafeText
from django.test.client import RequestFactory
from shipping.tests.test_views import ShippingTestCaseBase
from life.models import Tree, Locale, Forest
from mbdb.models import Build
from .models import Run, Active
from .templatetags.run_filters import showrun
from elmo_commons.tests.mixins import EmbedsTestCaseMixin
from html5lib import parseFragment
import l10nstats.views
import shipping.views


class L10nstatsTestCase(ShippingTestCaseBase, EmbedsTestCaseMixin):
    fixtures = ['one_started_l10n_build.json']

    def _create_active_run(self):
        locale, __ = Locale.objects.get_or_create(
          code='en-US',
          name='English',
        )
        tree = Tree.objects.all()[0]
        build = Build.objects.all()[0]
        run = Run.objects.create(
          locale=locale,
          tree=tree,
          build=build,
          srctime=datetime.datetime.utcnow(),
        )
        Active.objects.create(run=run)
        return run

    def test_history_static_files(self):
        """render the tree_status view and check that all static files are
        accessible"""
        appver, tree = self._create_appver_tree()
        url = reverse('locale-tree-history')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)
        locale, __ = Locale.objects.get_or_create(
          code='en-US',
          name='English',
        )
        data = {'tree': tree.code, 'locale': locale.code}
        # good locale, good tree, but not building
        response = self.client.get(url, data)
        self.assertEqual(response.status_code, 404)
        # good locale, good tree, and building, 200
        self._create_active_run()
        response = self.client.get(url, data)
        self.assertEqual(response.status_code, 200)
        self.assert_all_embeds(response.content)

    def test_tree_status_static_files(self):
        """render the tree_status view and check that all static files are
        accessible"""
        appver, tree = self._create_appver_tree()

        url = reverse('tree-history', args=['XXX'])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

        # _create_appver_tree() creates a mock tree
        url = reverse('tree-history', args=[tree.code])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        content = force_text(response.content)
        self.assertIn('no statistics for %s' % tree.code, content)

        self._create_active_run()
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        self.assert_all_embeds(response.content)

    def test_render_index_legacy(self):
        """the old dashboard should redirect to the shipping dashboard"""
        url = reverse(l10nstats.views.index)
        response = self.client.get(url)

        self.assertEqual(response.status_code, 301)
        self.assertIn(
            reverse(shipping.views.index),
            urlparse(response['location']).path)

        # now try it with a query string as well
        response = self.client.get(url, {'av': 'fx 1.0'})
        self.assertEqual(response.status_code, 301)

        qd = QueryDict(urlparse(response['location']).query)
        self.assertEqual(qd['av'], 'fx 1.0')
        self.assertIn(
            reverse(shipping.views.index),
            urlparse(response['location']).path)

    def test_compare_with_invalid_id(self):
        """trying to run a compare with an invalid Run ID shouldn't cause a 500
        error. Instead it should return a 400 error.

        See https://bugzilla.mozilla.org/show_bug.cgi?id=698634
        """

        url = reverse('compare-locales')
        response = self.client.get(url, {'run': 'xxx'})
        self.assertEqual(response.status_code, 404)

        # and sane but unknown should be 404
        response = self.client.get(url, {'run': 123})
        self.assertEqual(response.status_code, 404)


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


doc_v1 = {
    "_index": "elmo-comparisons",
    "_type": "comparison",
    "_id": "729457",
    "_version": 1,
    "_source": {
        "run": 729457,
        "details": {
            "children": [
                ["fr",
                 {
                     "children": [
                         ["dom/chrome/dom/dom.properties",
                          {
                              "value": {"missingEntity": [
                                  "MozAutoGainControlWarning",
                                  "MozNoiseSuppressionWarning"
                                  ]}
                          }],
                         ["mobile/android/chrome/browser.properties",
                          {
                              "value": {"missingEntity": [
                                  "alertShutdownSanitize"
                                  ]}
                          }]
                          ]
                 }]
                 ]
        }
    }
}


doc_v2 = {
    "_index": "elmo-comparisons",
    "_type": "comparison",
    "_id": "729457",
    "_version": 1,
    "_source": {
        "run": 729457,
        "details": {
            "fr": {
                "dom/chrome/dom/dom.properties": [
                    {"missingEntity": "MozNoiseSuppressionWarning"},
                    {"missingEntity": "MozAutoGainControlWarning"},
                ],
                "mobile/android/chrome/browser.properties": [
                    {"missingEntity": "alertShutdownSanitize"},
                ]
            }
        }
    }
}


class TestCompareView(TestCase):
    def setUp(self):
        l10n = Forest.objects.create(
            name='l10n',
            url='http://localhost:8001/l10n/')
        tree = Tree.objects.create(code='fx', l10n=l10n)
        locale = Locale.objects.create(code='de')
        self.run = Run.objects.create(
            tree=tree,
            locale=locale,
            missing=10,
            changed=10,
            total=20,
            id=doc_v1['_source']['run']
        )

    def test_compare_view_legacy(self):

        class View(l10nstats.views.CompareView):
            def get_doc(self, run):
                return doc_v1['_source']
        self._check_view(View)

    def test_compare_view(self):

        class View(l10nstats.views.CompareView):
            def get_doc(self, run):
                return doc_v2['_source']
        self._check_view(View)

    def _check_view(self, View):
        rf = RequestFactory()
        r = View.as_view()(rf.get('/foo/', {'run': str(self.run.id)}))
        context = r.context_data
        self.assertEqual(len(context['nodes']), 1)
        node = context['nodes'][0]
        self.assertEqual(node.path, 'fr')
        children = list(node)
        self.assertEqual(len(children), 2)
        node = children[1]  # just check the second, good enough
        self.assertEqual(
            node.fragment,
            'mobile/android/chrome/browser.properties')
        self.assertListEqual(
            node.entities, [
                {'key': 'alertShutdownSanitize', 'class': 'missing'}
            ])
        self.assertDictEqual(context['widths'], {
            'changed': 150,
            'missing': 150,
            'missingInFiles': 0,
            'report': 0,
            'unchanged': 0
        })
