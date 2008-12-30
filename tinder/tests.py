import unittest
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
        rv = waterfall(None)
        import pdb
        pdb.set_trace()
        self.assertTrue(len(rv.content) > 0, 'Html content should be there')
