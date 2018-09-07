# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
from __future__ import absolute_import
from __future__ import unicode_literals

import os
from django.test import TestCase as OrigTestCase
from django.test import override_settings
from django.test.runner import DiscoverRunner


class TestRunner(DiscoverRunner):
    """This is a test runner that adds apps to discover."""
    def build_suite(self, test_labels=None, extra_tests=None, **kwargs):
        if not test_labels:
            extra_tests = self.test_loader.discover(start_dir='apps', **kwargs)
        return super(TestRunner, self).build_suite(
            test_labels=test_labels,
            extra_tests=extra_tests,
            **kwargs)


def env(suffix, default):
    key = 'ELMO_TEST_' + suffix
    if key not in os.environ:
        return default
    val = os.environ[key].lower()
    return val in ['1', 'true']


@override_settings(
    L10N_FEED_URL='''<?xml version="1.0"?>
<feed xmlns="http://www.w3.org/2005/Atom">
</feed>
''',
    COMPRESS_ENABLED=env('COMPRESS_ENABLED', True),
    COMPRESS_OFFLINE=env('COMPRESS_OFFLINE', False),
)
class TestCase(OrigTestCase):
    pass
