import unittest
import os
from django.test import TestCase

from tinder.views import _waterfall, waterfall

class WaterfallStarted(TestCase):
    fixtures = ['one_started_l10n_build.json']

    def testInner(self):
        '''Basic tests of _waterfall'''
        blame, buildercolumns, filters, times = _waterfall(None)
        self.assertEqual(blame.width, 1,
                         'Width of blame column is not 1')
        self.assertEqual(len(buildercolumns), 1,
                         'Not one builder found')
        name, builder = buildercolumns.items()[0]
        self.assertEqual(name, 'dummy')
        self.assertEqual(builder.width, 1,
                         'Width of builder column is not 1')
        blame_rows = list(blame.rows())
        self.assertEqual(len(blame_rows), 3,
                         'Expecting 3 rows for table')
        self.assertNotEqual(blame_rows[0], [],
                            'First row should not be empty')
        self.assertEqual(blame_rows[1], [])
        self.assertEqual(blame_rows[2], [])
        build_rows = list(builder.rows())
        self.assertEqual(build_rows[0][0]['obj'].buildnumber, 1)
        self.assertEqual(build_rows[1][0]['obj'].buildnumber, 0)
        self.assertEqual(build_rows[2][0]['obj'], None)

    def testHtml(self):
        resp = waterfall(None)
        self.assertTrue(resp.status_code, 200)        
        self.assertTrue(len(resp.content) > 0, 'Html content should be there')

class WaterfallParallel(TestCase):
    fixtures = ['parallel_builds.json']

    def testInner(self):
        '''Testing parallel builds in _waterfall'''
        blame, buildercolumns, filters, times = _waterfall(None)

    def testHtml(self):
        '''Testing parallel builds in _waterfall'''
        resp = waterfall(None)
        self.assertTrue(resp.status_code, 200)        
        self.assertTrue(len(resp.content) > 0, 'Html content should be there')

class FullBuilds(TestCase):
    fixtures = ['full_parallel_ builds.json']

    def testInner(self):
        '''Testing full build list in _waterfall'''
        blame, buildercolumns, filters, times = _waterfall(None)

    def testForBuild(self):
        pass

from windmill.authoring import djangotest
class WindMillTest(djangotest.WindmillDjangoUnitTest):
    test_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'windmilltests')
    browser = 'firefox'
    fixtures = ['full_parallel_builds.json']

    def testTest(self):
        import pdb
        pdb.set_trace()
