# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
from __future__ import absolute_import

from test_utils import TestCase as OrigTestCase
import django_nose
from django.conf import settings


class TestSuiteRunner(django_nose.NoseTestSuiteRunner):
    """This is a test runner that pulls in settings_test.py."""
    def setup_test_environment(self, **kwargs):
        # If we have a settings_test.py let's roll it into our settings.
        try:
            import settings_test
            # Use setattr to update Django's proxies:
            for k in dir(settings_test):
                setattr(settings, k, getattr(settings_test, k))
        except ImportError:
            pass
        super(TestSuiteRunner, self).setup_test_environment(**kwargs)


class TestCase(OrigTestCase):
    pass
