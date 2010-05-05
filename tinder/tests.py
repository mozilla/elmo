# ***** BEGIN LICENSE BLOCK *****
# Version: MPL 1.1/GPL 2.0/LGPL 2.1
#
# The contents of this file are subject to the Mozilla Public License Version
# 1.1 (the "License"); you may not use this file except in compliance with
# the License. You may obtain a copy of the License at
# http://www.mozilla.org/MPL/
#
# Software distributed under the License is distributed on an "AS IS" basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied. See the License
# for the specific language governing rights and limitations under the
# License.
#
# The Original Code is l10n django site.
#
# The Initial Developer of the Original Code is
# Mozilla Foundation.
# Portions created by the Initial Developer are Copyright (C) 2010
# the Initial Developer. All Rights Reserved.
#
# Contributor(s):
#
# Alternatively, the contents of this file may be used under the terms of
# either the GNU General Public License Version 2 or later (the "GPL"), or
# the GNU Lesser General Public License Version 2.1 or later (the "LGPL"),
# in which case the provisions of the GPL or the LGPL are applicable instead
# of those above. If you wish to allow use of your version of this file only
# under the terms of either the GPL or the LGPL, and not to allow others to
# use your version of this file under the terms of the MPL, indicate your
# decision by deleting the provisions above and replace them with the notice
# and other provisions required by the GPL or the LGPL. If you do not delete
# the provisions above, a recipient may use your version of this file under
# the terms of any one of the MPL, the GPL or the LGPL.
#
# ***** END LICENSE BLOCK *****

'''Tests for the build progress displays.
'''

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
    fixtures = ['full_parallel_builds.json']

    def testInner(self):
        '''Testing full build list in _waterfall'''
        blame, buildercolumns, filters, times = _waterfall(None)

    def testForBuild(self):
        pass

#from windmill.authoring import djangotest
#class WindMillTest(djangotest.WindmillDjangoUnitTest):
#    test_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'windmilltests')
#    browser = 'firefox'
#    fixtures = ['full_parallel_builds.json']
#
#    def testTest(self):
#        import pdb
#        pdb.set_trace()
