# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
from __future__ import absolute_import

import os
import shutil
import tempfile
from django.conf import settings
from django.test import override_settings
from elmo.test import TestCase
from life.models import Repository
from ..utils import get_or_create_changeset


class RepoTestBase(TestCase):
    def setUp(self):
        super(RepoTestBase, self).setUp()
        self._settings_context = override_settings(
            REPOSITORY_BASE=tempfile.mkdtemp())
        self._settings_context.enable()
        self.repo = os.path.join(settings.REPOSITORY_BASE, self.repo_name)

    def tearDown(self):
        if os.path.isdir(settings.REPOSITORY_BASE):
            shutil.rmtree(settings.REPOSITORY_BASE)
        self._settings_context.disable()
        super(RepoTestBase, self).tearDown()

    def dbrepo(self, name=None, changesets_from=None, revrange=None,
               urlpattern='http://localhost:8001/%s/'):
        if name is None:
            name = self.repo_name
        repo = Repository.objects.create(
          name=name,
          url=urlpattern % name
        )
        if changesets_from is None:
            return repo
        if revrange is None:
            revrange = 'head()'
        for rev in changesets_from.log(revrange=revrange):
            ctx = changesets_from[rev]
            get_or_create_changeset(repo, changesets_from, ctx)
        return repo
