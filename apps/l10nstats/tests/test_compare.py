# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
from __future__ import absolute_import
from __future__ import unicode_literals

from elmo.test import TestCase
from django.test.client import RequestFactory
from django.core.urlresolvers import reverse
from life.models import Tree, Locale, Forest
from ..models import Run
from l10nstats.views import compare


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

    def test_compare_view_legacy(self):

        class View(compare.CompareView):
            def get_doc(self, run):
                return doc_v1['_source']
        self._check_view(View)

    def test_compare_view(self):

        class View(compare.CompareView):
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
