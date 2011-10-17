# Copyright (C) 2010, 2011 Linaro Limited
#
# Author: Zygmunt Krynicki <zygmunt.krynicki@linaro.org>
#
# This file is part of versiontools.
#
# versiontools is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License version 3
# as published by the Free Software Foundation
#
# versiontools is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with versiontools.  If not, see <http://www.gnu.org/licenses/>.
import sys

from distutils.dist import Distribution
from distutils.errors import DistutilsSetupError

from unittest import TestCase

from versiontools import Version, handle_version


class VersionFormattingTests(TestCase):

    def setUp(self):
        # Inhibit Version.vcs from working
        self._real_vcs = Version.vcs
        Version.vcs = property(lambda self: None)

    def tearDown(self):
        Version.vcs = self._real_vcs

    def test_defaults(self):
        self.assertEqual(Version(1, 0), (1, 0, 0, "final", 0))

    def test_serial_cannot_be_zero_for_certain_releaselevel(self):
        self.assertRaises(ValueError, Version, 1, 2, 3, "alpha", 0)
        self.assertRaises(ValueError, Version, 1, 2, 3, "beta", 0)
        self.assertRaises(ValueError, Version, 1, 2, 3, "candidate", 0)

    def test_serial_can_be_zero_for_certain_releaselevel(self):
        self.assertEqual(Version(1, 2, 3, "final", 0).serial, 0)
        self.assertEqual(Version(1, 2, 3, "dev", 0).serial, 0)

    def test_releaselevel_values(self):
        self.assertRaises(ValueError, Version, 1, 2, 3, "foobar", 0)

    def test_accessors(self):
        version = Version(1, 2, 3, "dev", 4)
        self.assertEqual(version.major, 1)
        self.assertEqual(version.minor, 2)
        self.assertEqual(version.micro, 3)
        self.assertEqual(version.releaselevel, "dev")
        self.assertEqual(version.serial, 4)

    def test_positional_accessors(self):
        version = Version(1, 2, 3, "dev", 4)
        self.assertEqual(version[0], 1)
        self.assertEqual(version[1], 2)
        self.assertEqual(version[2], 3)
        self.assertEqual(version[3], "dev")
        self.assertEqual(version[4], 4)

    def test_formatting_zero_micro_discarded(self):
        self.assertEqual(str(Version(1, 0)), "1.0")
        self.assertEqual(str(Version(1, 0, 0)), "1.0")

    def test_formatting_nonzero_micro_retained(self):
        self.assertEqual(str(Version(1, 0, 1)), "1.0.1")

    def test_formatting_serial_not_used_for_development(self):
        self.assertEqual(str(Version(1, 2, 3, "dev", 4)), "1.2.3.dev")

    def test_formatting_serial_not_used_for_final(self):
        self.assertEqual(str(Version(1, 2, 3, "final", 4)), "1.2.3")

    def test_formatting_serial_used_for_alpha_beta_and_candidate(self):
        self.assertEqual(str(Version(1, 2, 3, "alpha", 4)), "1.2.3a4")
        self.assertEqual(str(Version(1, 2, 3, "beta", 4)), "1.2.3b4")
        self.assertEqual(str(Version(1, 2, 3, "candidate", 4)), "1.2.3c4")


class MockedVCS(object):

    def __init__(self, revno):
        self.revno = revno


class VersionFormattingTestsWithMockedVCS(TestCase):

    def setUp(self):
        # Inhibit Version.vcs from working
        self._real_vcs = Version.vcs
        self.mocked_vcs = None
        Version.vcs = property(lambda x: self.mocked_vcs)

    def mock_vcs_revno(self, revno):
        self.mocked_vcs = MockedVCS(revno)

    def tearDown(self):
        Version.vcs = self._real_vcs

    def test_formatting_without_vcs(self):
        version = Version(1, 2, 3, "dev", 4)
        self.assertEqual(str(version), "1.2.3.dev")

    def test_formatting_with_vcs_and_revno(self):
        self.mock_vcs_revno(5)
        version = Version(1, 2, 3, "dev", 4)
        self.assertEqual(str(version), "1.2.3.dev5")

    def test_formatting_no_dev_suffix_for_alpha_beta_and_candidate(self):
        self.mock_vcs_revno(5)
        self.assertEqual(str(Version(1, 2, 3, "alpha", 4)), "1.2.3a4")
        self.assertEqual(str(Version(1, 2, 3, "beta", 4)), "1.2.3b4")
        self.assertEqual(str(Version(1, 2, 3, "candidate", 4)), "1.2.3c4")


class HandleVersionTests(TestCase):

    def setUp(self):
        self.dist = Distribution()

    def test_cant_import(self):
        version = ':versiontools:nonexisting:'
        try:
            handle_version(self.dist, None, version)
        except Exception:
            e = sys.exc_info()[1]
            self.assertTrue(isinstance(e, DistutilsSetupError))
            self.assertEqual(str(e), "Unable to import 'nonexisting': "
                                      "No module named nonexisting")

    def test_not_found(self):
        version = ':versiontools:versiontools:__nonexisting__'
        try:
            handle_version(self.dist, None, version)
        except Exception:
            e = sys.exc_info()[1]
            self.assertTrue(isinstance(e, DistutilsSetupError))
            self.assertEqual(str(e), "Unable to access '__nonexisting__' in "
                                      "'versiontools': 'module' object has "
                                      "no attribute '__nonexisting__'")
